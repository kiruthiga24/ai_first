# rag.py
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(EMBED_MODEL_NAME)

chroma_client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./memory_store"))
rag_collection = chroma_client.get_or_create_collection(name="pii_docs")

def ingest_text(name, text):
    emb = embedding_model.encode([text]).tolist()
    rag_collection.add(documents=[text], ids=[name], embeddings=emb)

def _flatten_documents(raw_docs):
    out = []
    if not raw_docs:
        return out
    for item in raw_docs:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            for key in ("document", "text", "content"):
                if key in item and isinstance(item[key], str):
                    out.append(item[key])
                    break
            else:
                out.append(str(item))
        elif isinstance(item, (list, tuple)):
            for sub in item:
                if isinstance(sub, str):
                    out.append(sub)
                elif isinstance(sub, dict):
                    for key in ("document", "text", "content"):
                        if key in sub and isinstance(sub[key], str):
                            out.append(sub[key])
                            break
                    else:
                        out.append(str(sub))
                else:
                    out.append(str(sub))
        else:
            out.append(str(item))
    seen = set()
    cleaned = []
    for s in out:
        s2 = s.strip()
        if not s2:
            continue
        if s2 in seen:
            continue
        seen.add(s2)
        cleaned.append(s2)
    return cleaned

def rag_query(query, n_results: int = 3):
    emb = embedding_model.encode([query]).tolist()
    res = rag_collection.query(query_embeddings=emb, n_results=n_results)
    raw_docs = res.get("documents") if isinstance(res, dict) else None
    return _flatten_documents(raw_docs)

def get_combined_rag_text(query=None, n_results: int = 5):
    if query:
        docs = rag_query(query, n_results=n_results)
    else:
        try:
            all_docs = rag_collection.get(include=["documents"])
            raw = all_docs.get("documents", [])
            docs = _flatten_documents(raw)
        except Exception:
            docs = rag_query("", n_results=n_results)
    combined = "\n\n".join(docs)
    return combined
