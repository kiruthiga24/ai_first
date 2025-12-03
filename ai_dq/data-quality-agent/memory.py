# memory.py
import json
import os

MEM_PATH = "memory_store/memory.json"
if not os.path.exists("memory_store"):
    os.makedirs("memory_store")

def load_memory():
    if os.path.exists(MEM_PATH):
        return json.load(open(MEM_PATH, "r", encoding="utf-8"))
    return {}

def save_memory(mem):
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2, ensure_ascii=False)
