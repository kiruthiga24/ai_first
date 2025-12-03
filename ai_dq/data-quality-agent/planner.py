# planner.py
import os
import subprocess
import requests
import json
from prompts import PLANNER_SYSTEM_PROMPT

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
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            print(data)
            return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(e)
    

def planner_agent(profile):
    prompt = f"""
{PLANNER_SYSTEM_PROMPT}

DATASET PROFILE:
{json.dumps(profile, indent=2)}

Return the JSON only.
"""
    res = llama_run(prompt)
    # parse JSON robustly
    try:
        return json.loads(res)
    except:
        import re
        m = re.search(r'(\{[\s\S]*\})', res)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
    # fallback simple plan
    fallback = {"steps": ["schema_check", "null_check", "duplicate_check", "format_check"], "notes": "fallback plan"}
    return fallback
