# tools.py
import pandas as pd
import os
from shutil import copyfile

def load_data(csv_path):
    df = pd.read_csv(csv_path)
    return df

def backup_csv(csv_path):
    backup_path = csv_path + ".bak"
    copyfile(csv_path, backup_path)
    return backup_path

def restore_csv(backup_path, target_path):
    copyfile(backup_path, target_path)

def analyze_data(df):
    profile = {}
    profile["num_rows"] = int(len(df))
    profile["schema"] = {col: str(df[col].dtype) for col in df.columns}
    profile["null_counts"] = {col: int(df[col].isna().sum()) for col in df.columns}
    profile["null_percent"] = {col: float(df[col].isna().mean()) for col in df.columns}
    profile["dup_rows"] = int(df.duplicated().sum())
    invalids = {}
    if "email" in df.columns:
        # treat NaN as invalid for format counts
        invalid_mask = ~df['email'].astype(str).str.match(r"[^@]+@[^@]+\.[^@]+")
        invalids["email_invalid_count"] = int(invalid_mask.sum())
    if "price" in df.columns:
        try:
            neg_count = int((df['price'].astype(float) < 0).sum())
        except Exception:
            neg_count = 0
        invalids["price_negative_count"] = neg_count

    profile["invalids"] = invalids
    
    return profile

def apply_fixes(df, actions):
    df2 = df.copy()
    for action in actions:
        act = action.get("action")
        params = action.get("params", {})
        print("inside for")
        print(act)
        print(params)

        if act == "drop_duplicates":
            subset = params.get("subset", None)
            if subset:
                subset = [c for c in subset if c in df2.columns]
                if subset:
                    df2.drop_duplicates(subset=subset, inplace=True)
            else:
                df2.drop_duplicates(inplace=True)

        elif act == "impute_nulls":
            col = params.get("column")
            strategy = params.get("strategy", "constant")
            if col in df2.columns:
                if strategy == "mean" and pd.api.types.is_numeric_dtype(df2[col]):
                    df2[col].fillna(df2[col].mean(), inplace=True)
                elif strategy == "median" and pd.api.types.is_numeric_dtype(df2[col]):
                    df2[col].fillna(df2[col].median(), inplace=True)
                else:
                    df2[col].fillna(params.get("value", ""), inplace=True)

        elif act == "normalize_email":
            col = params.get("column", "email")
            if col in df2.columns:
                df2[col] = df2[col].astype(str).str.strip().str.lower()

        elif act == "regex_clean":
            col = params.get("column")
            pattern = params.get("pattern")
            repl = params.get("repl", "")
            if col in df2.columns and pattern:
                df2[col] = df2[col].astype(str).str.replace(pattern, repl, regex=True)

        # 🆕 NEW CONSERVATIVE FIX
        elif act == "remove_negative_values":
            col = params.get("column")
            print("inside fixes")
            print(col)
            if col in df2.columns and pd.api.types.is_numeric_dtype(df2[col]):
                print("inside if")
                df2.loc[df2[col] < 0, col] = None  # Null out invalid negatives

        else:
            # unknown action - ignore
            continue

    return df2


def evaluate_improvement(before_df, after_df):
    before = analyze_data(before_df)
    after = analyze_data(after_df)
    before_score = sum(before["invalids"].values()) + before["dup_rows"]
    after_score = sum(after["invalids"].values()) + after["dup_rows"]
    improved = after_score < before_score
    return {
        "improved": improved,
        "before_score": int(before_score),
        "after_score": int(after_score),
        "before_profile": before,
        "after_profile": after
    }
