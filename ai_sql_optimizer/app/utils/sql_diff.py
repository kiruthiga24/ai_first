import difflib

def generate_diff(before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="before.sql",
        tofile="after.sql"
    ))
