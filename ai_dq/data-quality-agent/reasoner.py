# reasoner.py
import subprocess
import json
import re
import requests
from prompts import REASONER_SYSTEM_PROMPT
from rag import get_combined_rag_text, rag_query
from policies import KNOWN_POLICIES, KNOWN_POLICIES_LOWER

def llama_run(prompt_text):
    try:
        new_api_url = "http://localhost:11434/v1/chat/completions"
        response = requests.post(
            new_api_url,
            json={
                "model": "llama3:latest",
                "messages": [
                    {"role": "user", "content": prompt_text}
                ]
            },
            timeout=300
        )

        if response.status_code == 200:
            data = response.json()
            print(data)
            return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(e)
    

def extract_json(raw):
    if not raw:
        return None
    # try direct parse
    try:
        return json.loads(raw)
    except:
        pass
    # Fallback: regex to isolate JSON object
    m = re.search(r'(\{[\s\S]*\})', raw)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            return None
    return None


def _validate_proposed_schema(obj):
    """
    Ensure proposed_fixes JSON follows strict schema required by system.
    """
    if not isinstance(obj, dict):
        return False
    if "proposed_fixes" not in obj or not isinstance(obj["proposed_fixes"], list):
        return False
    for fx in obj["proposed_fixes"]:
        if not all(k in fx for k in ("id", "description", "action", "params", "policy_refs", "confidence")):
            return False
        # policy_refs must be list of dicts each with policy_id and quote
        if not isinstance(fx["policy_refs"], list):
            return False
        for pr in fx["policy_refs"]:
            if not isinstance(pr, dict) or "policy_id" not in pr or "quote" not in pr:
                return False
    return True

def reasoner_agent(profile, plan_steps, dataset_name=None):
    """
    Steps:
    1) Obtain combined RAG text relevant to dataset
    2) Build a short "policy inventory" of exact phrases that exist in RAG
    3) Pass profile + plan + matched policy phrases to LLM and ask for JSON
    4) Validate schema and ensure every policy_ref quote actually exists in combined text.
    """
    # 1) retrieve RAG context relevant to dataset or generic DQ
    query = f"data quality best practices for dataset: {dataset_name}" if dataset_name else "data quality best practices"
    rag_text = get_combined_rag_text(query=query, n_results=6).strip()
    rag_text_lower = rag_text.lower()

    # 2) match known policies by exact substring (lowercase)
    matched_policies = []
    for pid, phrase_lower in KNOWN_POLICIES_LOWER.items():
        if phrase_lower in rag_text_lower:
            matched_policies.append({"policy_id": pid, "quote": KNOWN_POLICIES[pid]})

    # Build inventory string for the model to use (explicit list)
    inventory_lines = []
    for mp in matched_policies:
        inventory_lines.append(f"{mp['policy_id']}: {mp['quote']}")
    inventory_text = "\n".join(inventory_lines) if inventory_lines else "No direct policy quotes found."

    prompt = f"""
{REASONER_SYSTEM_PROMPT}

DATASET PROFILE:
{json.dumps(profile, indent=2)}

PLANNER STEPS:
{json.dumps(plan_steps, indent=2)}

MATCHED_POLICY_INVENTORY:
{inventory_text}

RAG_SNIPPETS:
{rag_text}

Instructions:
- Use only the policies present in MATCHED_POLICY_INVENTORY to justify proposals.
- For each proposed fix, include policy_refs with policy_id from the inventory and the exact quote.
- If no matched policy supports a needed fix, do NOT propose it; instead add to questions_to_user.
- Output STRICT JSON only, matching the schema defined earlier.
"""
    raw = llama_run(prompt)

    # Attempt to parse JSON out of output robustly
    try:
        candidate = extract_json(raw)

        if not candidate or "proposed_fixes" not in candidate:
            # fallback if LLM didn’t behave
            return {
                "proposed_fixes": [],
                "questions_to_user": [
                    {
                        "question": "LLM did not return valid JSON — rerun?",
                        "related_columns": []
                    }
                ]
            }
    except Exception:
        m = re.search(r'(\{[\s\S]*\})', raw)
        candidate = None
        if m:
            try:
                candidate = json.loads(m.group(1))
            except Exception:
                candidate = None

    if not candidate or not _validate_proposed_schema(candidate):
        # If LLM failed or produced bad output, return safe fallback: ask a question instead
        return {"proposed_fixes": [], "questions_to_user": [{"question": "No conservative fix could be produced with policy grounding; please advise.", "related_columns": []}]}

    # Final sanity: ensure every quote exists in rag_text (case-insensitive)
    for fx in candidate["proposed_fixes"]:
        valid_refs = []
        for pr in fx.get("policy_refs", []):
            pid = pr.get("policy_id")
            quote = pr.get("quote", "")
            if pid in KNOWN_POLICIES and KNOWN_POLICIES[pid].lower() in rag_text_lower:
                valid_refs.append(pr)
        fx["policy_refs"] = valid_refs

    return candidate
