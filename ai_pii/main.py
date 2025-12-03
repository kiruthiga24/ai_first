# main.py
import os, json, time
from tools import load_data, analyze_data, apply_actions
from planner import planner_agent
from detector import detector_agent
from critic import critic_validate_plan, critic_validate_results
from memory import load_memory, save_memory
from rag import get_combined_rag_text, ingest_text

CSV_PATH = "data/sample_pii.csv"
BACKUP_SUFFIX = ".bak"

def backup_csv(path):
    import shutil
    b = path + BACKUP_SUFFIX
    shutil.copyfile(path, b)
    return b

def restore_csv(backup, target):
    import shutil
    shutil.copyfile(backup, target)

def ingest_docs_if_needed():
    docs_path = "docs/gdpr_rules.txt"
    if os.path.exists(docs_path):
        text = open(docs_path,"r",encoding="utf-8").read()
        ingest_text("gdpr_rules", text)

def print_risk_report(profile):
    print("\n================= PII RISK REPORT =================")
    print("| Column | Risk Score | Risk Level |")
    print("|--------|------------|------------|")

    for col, score in profile.get("risk_scores", {}).items():
        level = (
            "HIGH 🚨" if score >= 70 else
            "MEDIUM ⚠️" if score >= 40 else
            "LOW 🟢"
        )
        print(f"| {col} | {score} | {level} |")

def main():
    ingest_docs_if_needed()
    backup = backup_csv(CSV_PATH)
    print(f"[INFO] Backup created: {backup}")

    df = load_data(CSV_PATH)
    profile = analyze_data(df)
    profile = json.loads(json.dumps(profile, default=str))
    print("[INFO] Profile:")
    print(profile["ner_signals"])
    print(profile["embedding_signals"])
    print(json.dumps(profile, indent=2)[:1000])

    plan = planner_agent(profile)
    print("[INFO] Planner steps:", plan)

    detector_out = detector_agent(df, profile, plan.get("steps", []), dataset_name=os.path.basename(CSV_PATH))
    print("[INFO] Detector proposed:")
    print(json.dumps(detector_out, indent=2))

    validated = critic_validate_plan(profile, detector_out, dataset_name=os.path.basename(CSV_PATH))
    print("[INFO] Critic validation:")
    print(json.dumps(validated, indent=2))

    # If revision required, show suggested changes and abort for simplicity
    if validated.get("overall_decision") != "accept":
        print("[WARN] Plan needs revision per critic. Suggested changes:", validated.get("suggested_changes"))
        # For demo purposes, we stop and ask human to review.
        return

    actions = [ { "id": a["id"], "action": a["action"], "params": a["params"] } for a in detector_out.get("proposed_actions", []) ]
    if not actions:
        print("[INFO] No actions to apply.")
        return

    # Ask user approval (CLI)
    print("[INFO] Actions to apply:")
    for a in actions:
        print("-", a)
    approval = input("Apply actions? (Y/N): ").strip().lower()
    if approval != "y":
        print("[INFO] Execution aborted by user.")
        return

    # Execute
    try:
        new_df = apply_actions(df, actions)
        out_path = "data/pii_masked_output.csv"
        new_df.to_csv(out_path, index=False)
        print("[INFO] Actions applied. Output saved to", out_path)
    except Exception as e:
        print("[ERROR] Execution failed:", e)
        restore_csv(backup, CSV_PATH)
        return

    print("[INFO] Risk Report:")
    print_risk_report(profile)


    # Post validation (simple)
    after_profile = analyze_data(new_df)
    post = critic_validate_results(profile, after_profile, detector_out, dataset_name=os.path.basename(CSV_PATH))
    print("[INFO] Post validation:", post)

    # Save memory history
    mem = load_memory()
    mem.setdefault("pii_runs", []).append({
        "timestamp": int(time.time()),
        "dataset": os.path.basename(CSV_PATH),
        "plan": detector_out,
        "post_validation": post
    })
    save_memory(mem)
    print("[DONE] Run complete. Memory updated.")

if __name__ == "__main__":
    main()
