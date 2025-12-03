# detector.py
import subprocess, os, json, re, time
from prompts import DETECTOR_SYSTEM_PROMPT
from rag import get_combined_rag_text
from tools import analyze_data
import requests

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
            timeout=500
        )

        if response.status_code == 200:
            data = response.json()
            print(data)
            return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(e)
# robust JSON extraction helper
def extract_json(raw):
    if not raw or not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r'(\{[\s\S]*\})', raw)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
    return None

def detector_agent(df, profile, planner_steps, dataset_name=None):
    rag_text = get_combined_rag_text(query=dataset_name, n_results=6)
    prompt = f"""{DETECTOR_SYSTEM_PROMPT}

DATASET PROFILE:
{json.dumps(profile, indent=2)}

PLANNER STEPS:
{json.dumps(planner_steps, indent=2)}

RAG_SNIPPETS:
{rag_text}

Return JSON only.
"""
    raw = llama_run(prompt)
    candidate = extract_json(raw)
    # validation + normalization
    if not candidate or "proposed_actions" not in candidate:
        return {"proposed_actions": [], "questions_to_user":[{"question":"LLM failed or no valid proposals; please advise.","related_columns":[]}]}
    # ensure columns exist
    valid_actions = []
    cols = set(profile.get("columns", []))
    for a in candidate.get("proposed_actions", []):
        params = a.get("params", {})
        col = params.get("column")
        if col and col in cols:
            valid_actions.append(a)
        else:
            # convert to question if column missing
            candidate.setdefault("questions_to_user", []).append({"question": f"Column {col} not found for action {a.get('id')}", "related_columns": []})
    candidate["proposed_actions"] = valid_actions
    candidate.setdefault("questions_to_user", [])
    return candidate
