import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os

# Initialize the embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Use the updated Chroma settings
# settings = Settings(
#     chroma_db_impl="duckdb+parquet",
#     persist_directory="./memory_store"
# )

# Initialize the Chroma client with the updated settings
chroma_client = chromadb.PersistentClient(path="./memory_store")

# chroma_client = chromadb.Client(settings)

# Get or create the collection
rag_collection = chroma_client.get_or_create_collection(name="dq_docs")

def ingest_text(name, text):
    emb = embedding_model.encode([text]).tolist()
    rag_collection.add(documents=[text], ids=[name], embeddings=emb)

def _flatten_documents(raw_docs):
    """
    Normalize various chroma output shapes into list of strings.
    raw_docs might be:
     - list of strings
     - nested lists
     - list of dicts like {"document": "..."} depending on version
    """
    out = []
    if raw_docs is None:
        return out
    # handle nested lists
    for item in raw_docs:
        if item is None:
            continue
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            # try common fields
            for key in ("document", "text", "content"):
                if key in item and isinstance(item[key], str):
                    out.append(item[key])
                    break
            else:
                # fallback to string representation
                out.append(str(item))
        elif isinstance(item, list) or isinstance(item, tuple):
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
    # remove empties and dedupe preserve order
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
    """
    Query and return a flattened list[str] of the top matched documents.
    """
    emb = embedding_model.encode([query]).tolist()
    res = rag_collection.query(query_embeddings=emb, n_results=n_results)
    # `res.get("documents")` may be nested; handle gracefully
    raw_docs = res.get("documents") if isinstance(res, dict) else None
    return _flatten_documents(raw_docs)

def get_combined_rag_text(query=None, n_results: int = 5):
    """
    If query provided, retrieve relevant documents; otherwise return all docs combined.
    Returns one large lowercase string for substring matching.
    """
    if query:
        docs = rag_query(query, n_results=n_results)
    else:
        # if no query, try retrieving all doc ids and fetch them (best-effort)
        try:
            # this call may return metadata/ids depending on chroma version
            all_docs = rag_collection.get(include=["documents"])  # may error on some versions
            raw = all_docs.get("documents", [])
            docs = _flatten_documents(raw)
        except Exception:
            # fallback: query an empty embedding to get something
            docs = rag_query("", n_results=n_results)
    combined = "\n\n".join(docs)
    return combined
