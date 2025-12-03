# main.py
import os
import json
from tools import load_data, analyze_data, backup_csv, restore_csv, apply_fixes, evaluate_improvement
from planner import planner_agent
from reasoner import reasoner_agent
from critic import critic_validate_plan, critic_validate_results
from memory import load_memory, save_memory
from rag import ingest_text
import time

CSV_PATH = "data/sample.csv"
SAFETY_MODE = "C"  # default: retry
MAX_RETRIES = 2

def ingest_docs_if_needed():
    docs_path = "docs/dq_best_practices.txt"
    if os.path.exists(docs_path):
        text = open(docs_path, "r", encoding="utf-8").read()
        ingest_text("dq_policies", text)

def main():
    ingest_docs_if_needed()

    backup_path = backup_csv(CSV_PATH)
    print(f"[INFO] Backup created at {backup_path}")

    df = load_data(CSV_PATH)
    profile = analyze_data(df)
    print("[INFO] Dataset profile:")
    print(json.dumps(profile, indent=2))

    dataset_name = os.path.basename(CSV_PATH)

    # Planner: produce steps (no fixes)
    plan = planner_agent(profile)
    print("[INFO] Planner steps:")
    print(json.dumps(plan, indent=2))

    # Reasoner: produce conservative fixes (must consult RAG)
    reasoner_out = reasoner_agent(profile, plan.get("steps", []), dataset_name=dataset_name)
    print("[INFO] Reasoner proposed:")
    print(json.dumps(reasoner_out, indent=2))

    # Critic validates plan BEFORE execution
    validated = critic_validate_plan(profile, reasoner_out, dataset_name=dataset_name)
    print("[INFO] Critic validation (pre-exec):")
    print(json.dumps(validated, indent=2))

    if validated.get("overall_decision") != "accept":
        print("[WARN] Plan requires revision according to critic.")
        if SAFETY_MODE == "A":
            print("[INFO] Stopping due to safety mode A.")
            return
        elif SAFETY_MODE == "B":
            print("[INFO] Requesting reasoner re-plan (safety B).")
            # Use critic suggested_changes to guide reasoner (pass as extra context)
            reasoner_out = reasoner_agent(profile, plan.get("steps", []), dataset_name=dataset_name)
            validated = critic_validate_plan(profile, reasoner_out, dataset_name=dataset_name)
            if validated.get("overall_decision") != "accept":
                print("[ERROR] Revised plan still not accepted. Exiting.")
                return
        else:
            print("[WARN] Proceeding despite critic objections (safety C).")

    # Build actions for execution from validated fixes
    fixes = [f for f in validated.get("validated_fixes", []) if f.get("status") == "accepted"]
    if not fixes:
        print("[INFO] No accepted fixes; nothing to apply.")
        return

    print("[INFO] Accepted fixes to apply:")
    print(fixes)
    for f in fixes:
        print("-", f.get("description"))

    approval = input("Apply fixes? (Y/N): ").strip().lower()
    if approval != "y":
        print("[INFO] Execution aborted by user.")
        return

    # Convert fixes to actions list for tools.apply_fixes
    actions = []
    for f in fixes:
        actions.append({"action": f.get("action"), "params": f.get("params", {})})

    before_df = df.copy()
    try:
        after_df = apply_fixes(df, actions)
        after_df.to_csv("data/cleaned_output.csv", index=False)
        print("[INFO] Applied fixes. Saved to data/cleaned_output.csv")
    except Exception as e:
        print("[ERROR] Exception during execution:", e)
        restore_csv(backup_path, CSV_PATH)
        print("[INFO] Rolled back CSV to backup.")
        return

    eval_result = evaluate_improvement(before_df, after_df)
    print("[INFO] Improvement evaluation:")
    print(json.dumps(eval_result, indent=2))

    post_validation = critic_validate_results(eval_result["before_profile"], eval_result["after_profile"], reasoner_out, dataset_name=dataset_name)
    print("[INFO] Critic validation (post-exec):")
    print(json.dumps(post_validation, indent=2))

    if not post_validation.get("accepted", False):
        print("[WARN] Post-validation failed or flagged non-compliance.")
        if SAFETY_MODE == "A":
            restore_csv(backup_path, CSV_PATH)
            print("[INFO] Rolled back due to safety A.")
            return
        elif SAFETY_MODE == "B":
            retries = 0
            success = False
            while retries < MAX_RETRIES and not success:
                print(f"[INFO] Retry attempt {retries+1}/{MAX_RETRIES}")
                # Use after_profile to replan
                plan = planner_agent(eval_result["after_profile"])
                reasoner_out = reasoner_agent(eval_result["after_profile"], plan.get("steps", []), dataset_name=dataset_name)
                validated = critic_validate_plan(eval_result["after_profile"], reasoner_out, dataset_name=dataset_name)
                if validated.get("overall_decision") == "accept":
                    fixes = [f for f in validated.get("validated_fixes", []) if f.get("status") == "accepted"]
                    actions = [{"action": f.get("action"), "params": f.get("params", {})} for f in fixes]
                    try:
                        new_after = apply_fixes(after_df, actions)
                        new_after.to_csv("data/cleaned_output.csv", index=False)
                        eval_result = evaluate_improvement(after_df, new_after)
                        post_validation = critic_validate_results(eval_result["before_profile"], eval_result["after_profile"], reasoner_out, dataset_name=dataset_name)
                        if post_validation.get("accepted", False):
                            print("[INFO] Retry successful.")
                            success = True
                            break
                        else:
                            after_df = new_after
                    except Exception as e:
                        print("[ERROR] Retry execution error:", e)
                retries += 1
            if not success:
                print("[ERROR] Retries exhausted. Rolling back to backup.")
                restore_csv(backup_path, CSV_PATH)
                return
        else:
            print("[WARN] Proceeding despite failed post-validation (safety C).")

    # record memory
    mem = load_memory()
    mem.setdefault("fix_history", []).append({
        "dataset": dataset_name,
        "timestamp": int(time.time()),
        "plan": reasoner_out,
        "post_validation": post_validation
    })
    save_memory(mem)
    print("[INFO] Memory updated with fix history.")
    print("[DONE] All complete.")

if __name__ == "__main__":
    main()
