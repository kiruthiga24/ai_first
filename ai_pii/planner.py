# planner.py
import json
import os
import requests
import subprocess
from prompts import PLANNER_SYSTEM_PROMPT

def llama_run(prompt_text, timeout):
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
            timeout=timeout
        )

        if response.status_code == 200:
            data = response.json()
            print(data)
            return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(e)

def planner_agent(profile):
    prompt = f"""{PLANNER_SYSTEM_PROMPT}

DATASET PROFILE:
{json.dumps(profile, indent=2)}

Return JSON only.
"""
    res = llama_run(prompt, timeout=300)
    if res:
        try:
            return json.loads(res)
        except Exception:
            pass
    # deterministic fallback
    return {"steps": ["schema_check","ner_check","email_regex","phone_regex","sensitive_terms_check"], "notes": "fallback plan"}
