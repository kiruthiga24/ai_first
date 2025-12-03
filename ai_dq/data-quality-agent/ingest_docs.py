# ingest_docs.py
from rag import ingest_text
import os

docs_path = "docs/dq_best_practices.txt"
if os.path.exists(docs_path):
    text = open(docs_path, "r", encoding="utf-8").read()
    ingest_text("dq_policies", text)
    print("Ingested dq_best_practices.txt into RAG collection.")
else:
    print("docs/dq_best_practices.txt not found.")
