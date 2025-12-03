# critic.py
import json
from rag import get_combined_rag_text

ALLOWED_ACTIONS = {"mask_email","mask_phone","hash_name","redact_address","mask_column"}

def critic_validate_plan(profile, plan, dataset_name=None):
    rag_text = get_combined_rag_text(query=dataset_name, n_results=6).lower()
    validated = {"validated_actions": [], "overall_decision": "accept", "suggested_changes": []}
    any_rejected = False
    proposed = plan.get("proposed_actions", [])
    cols = set(profile.get("columns", []))
    for a in proposed:
        aid = a.get("id")
        action = a.get("action")
        params = a.get("params", {})
        notes = []
        status = "accepted"
        # 1 action allowed
        if action not in ALLOWED_ACTIONS:
            status = "rejected"
            notes.append(f"Action '{action}' not allowed.")
        # 2 column exists
        col = params.get("column")
        if not col or col not in cols:
            status = "rejected"
            notes.append(f"Column '{col}' not present.")
        # 3 policy refs
        matched_refs = []
        for pr in a.get("policy_refs", []):
            quote = pr.get("quote","").strip()
            if quote and quote.lower() in rag_text:
                matched_refs.append(pr)
            else:
                notes.append(f"Policy quote not found: '{quote[:60]}...'")
        if not matched_refs:
            status = "rejected"
            notes.append("No valid policy_refs matched.")
        # 4 confidence gating
        conf = float(a.get("confidence", 0.0))
        if conf < 0.70:
            status = "rejected"
            notes.append(f"Low confidence {conf} < 0.70")
        if status == "rejected":
            any_rejected = True
            validated["suggested_changes"].append({"id": aid, "reason": " ; ".join(notes)})
        validated["validated_actions"].append({
            "id": aid,
            "description": a.get("description",""),
            "status": status,
            "notes": " ; ".join(notes) if notes else "Policy validated.",
            "policy_refs": matched_refs
        })
    validated["overall_decision"] = "accept" if not any_rejected else "revise"
    return validated

def critic_validate_results(before_profile, after_profile, plan, dataset_name=None):
    # Simple: check that masked columns have reduced sensitive counts (approx)
    # For now, base acceptance on absence of errors and that actions were applied.
    # Caller should extend with domain-specific checks.
    # We'll return accepted=True with high confidence as a placeholder if after_profile exists.
    accepted = True
    notes = "Post-exec validation not fully implemented; manual review recommended."
    confidence = 0.7
    return {"accepted": accepted, "notes": notes, "confidence": confidence}
