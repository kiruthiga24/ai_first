# run_test.py
import json
from tools import load_data, analyze_data
from planner import planner_agent
from reasoner import reasoner_agent
from critic import critic_validate_plan
from rag import get_combined_rag_text
import os

CSV_PATH = "data/sample.csv"
DATASET_NAME = os.path.basename(CSV_PATH)

def run_flow():
    df = load_data(CSV_PATH)
    profile = analyze_data(df)
    print("=== PROFILE ===")
    print(json.dumps(profile, indent=2))

    plan = planner_agent(profile)
    print("\n=== PLANNER STEPS ===")
    print(json.dumps(plan, indent=2))

    # show the combined rag snippets we will use
    rag_text = get_combined_rag_text(query=DATASET_NAME, n_results=6)
    print("\n=== RAG SNIPPETS (combined) ===")
    print(rag_text[:1000], "...\n")  # print first 1000 chars

    reasoner_out = reasoner_agent(profile, plan.get("steps", []), dataset_name=DATASET_NAME)
    print("\n=== REASONER OUTPUT ===")
    print(json.dumps(reasoner_out, indent=2))

    validated = critic_validate_plan(profile, reasoner_out, dataset_name=DATASET_NAME)
    print("\n=== CRITIC VALIDATION ===")
    print(json.dumps(validated, indent=2))

if __name__ == "__main__":
    run_flow()
