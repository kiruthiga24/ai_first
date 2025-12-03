# ingest_docs.py
from rag import ingest_text
import os

docs_path = "docs/gdpr_rules.txt"
if os.path.exists(docs_path):
    text = open(docs_path, "r", encoding="utf-8").read()
    ingest_text("gdpr_rules", text)
    print("Ingested gdpr_rules.txt into RAG collection.")
else:
    print("docs/gdpr_rules.txt not found.")
