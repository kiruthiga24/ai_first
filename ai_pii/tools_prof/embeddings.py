from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

PII_EXAMPLES = {
    "email": ["email", "mail", "gmail.com"],
    "phone": ["phone", "mobile", "+91"],
    "name": ["john doe", "firstname", "surname"],
    "dob": ["birthday", "date of birth", "dob"],
}

PII_EMBEDS = {
    k: model.encode(v, convert_to_tensor=True)
    for k,v in PII_EXAMPLES.items()
}

def detect_pii_embeddings(columns):
    col_emb = model.encode(columns, convert_to_tensor=True)
    scores = {}

    for i, col in enumerate(columns):
        scores[col] = {}
        for pii, emb in PII_EMBEDS.items():
            similarity = util.cos_sim(col_emb[i], emb).mean().item()
            scores[col][pii] = round(float(similarity), 3)

    return scores
