# tools.py
import pandas as pd
import re
import hashlib
import phonenumbers
from tools_prof.ner import detect_pii_ner
from tools_prof.embeddings import detect_pii_embeddings

def compute_risk_scores(profile):
    risk_scores = {}

    ner = profile.get("ner_signals", {})
    embeds = profile.get("embedding_signals", {})
    invalids = profile.get("invalids", {})

    for col in embeds.keys():
        score = 0

        # NER impact
        if col in ner:
            n = ner[col]
            score += n.get("PERSON", 0) * 5
            score += (n.get("GPE", 0) + n.get("LOC", 0)) * 4
            score += n.get("DATE", 0) * 4

        # Embedding impact
        e = embeds[col]
        if e.get("name", 0) > 0.7: score += 50
        if e.get("email", 0) > 0.7: score += 40
        if e.get("phone", 0) > 0.7: score += 40
        if e.get("dob", 0) > 0.7: score += 45

        # Invalid format penalties
        if "email_invalid_count" in invalids and "mail" in col:
            score += 10

        risk_scores[col] = min(score, 100)

    return risk_scores


def load_data(csv_path):
    return pd.read_csv(csv_path)

def analyze_data(df, sample_n=10):
    profile = {}
    profile["num_rows"] = int(len(df))
    profile["columns"] = list(df.columns)
    profile["schema"] = {col: str(df[col].dtype) for col in df.columns}
    profile["sample"] = df.head(sample_n).to_dict(orient="records")
    # basic metrics
    profile["null_counts"] = {col: int(df[col].isna().sum()) for col in df.columns}
    profile["ner_signals"] = detect_pii_ner(df)
    profile["embedding_signals"] = detect_pii_embeddings(list(df.columns))
    # email/phone invalid counts
    invalids = {}
    if "email" in df.columns:
        invalids["email_invalid_count"] = (~df["email"].astype(str).str.match(r"[^@]+@[^@]+\.[^@]+", na=False)).sum()
    if "phone" in df.columns:
        def phone_ok(x):
            try:
                pn = phonenumbers.parse(str(x), None)
                return phonenumbers.is_possible_number(pn) or phonenumbers.is_valid_number(pn)
            except Exception:
                return False
        invalids["phone_invalid_count"] = (~df["phone"].astype(str).fillna("").apply(phone_ok)).sum()

    # negative price detection
    if "price" in df.columns:
        try:
            neg_count = int((df['price'].astype(float) < 0).sum())
        except Exception:
            neg_count = 0
        invalids["price_negative_count"] = neg_count
    profile["invalids"] = invalids
    profile["risk_scores"] = compute_risk_scores(profile)
    return profile

# Masking utilities
def mask_email_localpart(email):
    if pd.isna(email) or str(email).strip() == "":
        return email
    s = str(email)
    if "@" not in s:
        return s
    local, domain = s.split("@", 1)
    if len(local) <= 2:
        local_masked = local[0] + "*"*(len(local)-1)
    else:
        local_masked = local[0] + "*"*(len(local)-2) + local[-1]
    return f"{local_masked}@{domain}"

def mask_phone_number(phone):
    if pd.isna(phone) or str(phone).strip() == "":
        return phone
    s = ''.join(ch for ch in str(phone) if ch.isdigit() or ch == '+')
    if len(s) <= 4:
        return "*" * len(s)
    # mask middle digits
    keep_prefix = 2
    keep_suffix = 2
    core = s[keep_prefix:len(s)-keep_suffix]
    return s[:keep_prefix] + "*"*len(core) + s[-keep_suffix:]

def hash_value(val, salt=""):
    if pd.isna(val):
        return val
    return hashlib.sha256((str(val) + salt).encode('utf-8')).hexdigest()[:12]

def redact_text(val):
    if pd.isna(val) or str(val).strip() == "":
        return val
    return "[REDACTED]"

def apply_actions(df, actions):
    df2 = df.copy()
    for act in actions:
        action = act.get("action")
        params = act.get("params", {})
        col = params.get("column")
        if not col or col not in df2.columns:
            continue
        if action == "mask_email":
            strategy = params.get("strategy", "mask_local")
            if strategy == "mask_local":
                df2[col] = df2[col].apply(mask_email_localpart)
        elif action == "mask_phone":
            df2[col] = df2[col].apply(mask_phone_number)
        elif action == "hash_name":
            salt = params.get("salt", "")
            df2[col] = df2[col].apply(lambda v: hash_value(v, salt))
        elif action == "redact_address":
            df2[col] = df2[col].apply(redact_text)
        elif action == "mask_column":
            # generic full-mask to star
            df2[col] = df2[col].apply(lambda v: "[MASKED]" if not pd.isna(v) else v)
        else:
            # skip unknown actions
            continue
    return df2
