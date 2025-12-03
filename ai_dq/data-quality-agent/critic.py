# critic.py
import json
import re
from prompts import CRITIC_SYSTEM_PROMPT
from rag import get_combined_rag_text
from policies import KNOWN_POLICIES, KNOWN_POLICIES_LOWER



def critic_validate_plan(profile, plan, dataset_name=None):
    # Flatten RAG text
    query = f"data quality best practices for dataset: {dataset_name}" if dataset_name else "data quality best practices"
    rag_text = get_combined_rag_text(query=query, n_results=6).lower()
    print(rag_text)

    validated = {"validated_fixes": [], "overall_decision": "accept", "suggested_changes": []}

    proposed = plan.get("proposed_fixes", [])
    if not proposed:
        validated["overall_decision"] = "accept"
        validated["validated_fixes"] = []
        return validated

    any_rejected = False
    for fx in proposed:
        fx_id = fx.get("id", "unknown")
        action = fx.get("action")
        params = fx.get("params")
        notes = []
        status = "accepted"

        # 1) confidence gating
        confidence = float(fx.get("confidence", 0.0))
        if confidence < 0.7:
            status = "rejected"
            notes.append(f"Low confidence ({confidence}) - threshold 0.7")

        # 2) verify each policy_ref quote exists as substring
        policy_refs = fx.get("policy_refs", [])
        matched_refs = []
        for pr in policy_refs:
            pid = pr.get("policy_id")
            quote = pr.get("quote", "").strip()
            if not quote:
                notes.append("Empty policy quote")
                continue
            if quote.lower() not in rag_text:
                notes.append(f"Policy quote not found in RAG: '{quote[:60]}...'")
                continue
            # found
            matched_refs.append(pr)

        if not matched_refs:
            status = "rejected"
            notes.append("No valid policy_refs matched the RAG text.")

        if status == "rejected":
            any_rejected = True
            # suggest safe alternative: convert fix to question for the user
            suggested = {
                "id": fx_id,
                "note": "Policy grounding missing. Consider asking the user to confirm this fix or provide policy text."
            }
            validated["suggested_changes"].append(suggested)

        validated["validated_fixes"].append({
            "id": fx_id,
            "action": action,
            "params": params,
            "description": fx.get("description", ""),
            "status": status,
            "notes": " ; ".join(notes) if notes else "Policy validated.",
            "policy_refs": matched_refs
        })

    validated["overall_decision"] = "accept" if not any_rejected else "revise"
    return validated

def critic_validate_results(before_profile, after_profile, plan, dataset_name=None):
    # Simple post-checking: use difference and ensure improvement + re-check policies for compliance
    # Here we compute simple score logic (caller should pass evaluate_improvement structure)
    # But we will also ensure any policy-based constraints hold (e.g., no negatives if RAG prohibits)
    rag_text = get_combined_rag_text(query=dataset_name, n_results=6).lower()
    # Basic improvement check: rely on before/after profiles
    before_invalids = sum(before_profile.get("invalids", {}).values()) + before_profile.get("dup_rows", 0)
    after_invalids = sum(after_profile.get("invalids", {}).values()) + after_profile.get("dup_rows", 0)
    improved = after_invalids < before_invalids

    # Compliance checks: if RAG-P5 exists (no negative numbers), verify price negative eliminated
    notes = []
    compliance = True
    if KNOWN_POLICIES_LOWER.get("RAG-P5", "") in rag_text:
        # check after_profile numeric negatives
        # caller provides profiles only; let's inspect after_profile invalids as proxy
        if after_profile.get("invalids", {}).get("price_negative_count", 0) > 0:
            compliance = False
            notes.append("Negative price values remain while policy prohibits negatives.")

    return {
        "accepted": improved and compliance,
        "notes": "Improved and compliant" if improved and compliance else "; ".join(notes) or "No improvement detected",
        "confidence": 0.9 if improved and compliance else 0.2
    }
