# policies.py
# Canonical mapping of policy_id -> exact phrase to match in RAG docs.
# Edit these strings if you change docs text.

KNOWN_POLICIES = {
    "RAG-P1": "Emails must follow the pattern: `username@domain.com`",
    "RAG-P2": "Phone numbers should include only valid characters (digits, spaces, dashes, parentheses).",
    "RAG-P3": "Required fields (e.g., email, phone) must not be null.",
    "RAG-P4": "Remove duplicate rows based on unique identifiers (e.g., `id`).",
    "RAG-P5": "Validate that numeric fields have no negative values unless explicitly allowed.",
    "RAG-P6": "Check that dates (e.g., `signup_date`) are not in the future.",
    "RAG-P7": "Null values should be imputed with appropriate defaults or flagged."
}

# Convenience: lowercased canonical phrases for substring matching
KNOWN_POLICIES_LOWER = {k: v.lower() for k, v in KNOWN_POLICIES.items()}
