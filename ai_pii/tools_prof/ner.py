import spacy

nlp = spacy.load("en_core_web_sm")

def detect_pii_ner(df):
    ner_report = {}

    for col in df.columns:
        text = " ".join(df[col].dropna().astype(str).head(20))
        if not text.strip():
            continue

        doc = nlp(text)

        ents = [ent.label_ for ent in doc.ents]
        ner_report[col] = {
            "PERSON": ents.count("PERSON"),
            "GPE": ents.count("GPE"),
            "LOC": ents.count("LOC"),
            "DATE": ents.count("DATE"),
        }

    return ner_report
