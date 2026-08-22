import pandas as pd
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dirty_data.ingest import ingest_raw_data

def generate_profile(df: pd.DataFrame) -> dict:
    profile = {
        "general": {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "completely_empty_rows": int((df == "").all(axis=1).sum()),
            "completely_empty_columns": [col for col in df.columns if (df[col] == "").all()]
        },
        "per_column": {},
        "identifiers": {},
        "dates": {},
        "categorical": {},
        "numeric": {}
    }
    
    for col in df.columns:
        is_empty = df[col] == ""
        non_empty_series = df[col][~is_empty]
        profile["per_column"][col] = {
            "dtype_ingested": str(df[col].dtype),
            "non_null_count": int((~is_empty).sum()),
            "null_count": int(is_empty.sum()),
            "null_percentage": float(is_empty.mean() * 100),
            "unique_count": int(df[col].nunique()),
            "sample_values": non_empty_series.head(5).tolist()
        }
    
    # Identifiers
    profile["identifiers"]["case_id"] = {
        "raw_unique_count": int(df["case_id"].nunique()),
        "exact_duplicate_count": int(df["case_id"].duplicated().sum()),
        "duplicate_raw_ids_examples": df[df["case_id"].duplicated()]["case_id"].head(5).tolist()
    }
    
    client_ref_empty = df["client_ref"] == ""
    profile["identifiers"]["client_ref"] = {
        "raw_unique_count": int(df["client_ref"].nunique()),
        "duplicate_count": int(df["client_ref"].duplicated().sum()),
        "missing_count": int(client_ref_empty.sum()),
        "representative_patterns": df["client_ref"][~client_ref_empty].head(5).tolist()
    }
    
    # Dates
    for d_col in ["intake_date", "closure_date"]:
        is_empty = df[d_col] == ""
        non_empty = df[d_col][~is_empty]
        profile["dates"][d_col] = {
            "raw_unique_count": int(df[d_col].nunique()),
            "missing_count": int(is_empty.sum()),
            "sample_formats": non_empty.head(10).tolist()
        }
        
    # Categorical
    for c_col in ["district", "status", "category", "priority"]:
        freq = df[c_col].value_counts().to_dict()
        profile["categorical"][c_col] = {
            "distinct_raw_values": int(df[c_col].nunique()),
            "frequency": {str(k): int(v) for k,v in freq.items()},
            "missing_count": int((df[c_col] == "").sum())
        }
        
    # Numeric
    freq_n = df["contact_count"].value_counts().to_dict()
    profile["numeric"]["contact_count"] = {
        "distinct_values": int(df["contact_count"].nunique()),
        "frequency": {str(k): int(v) for k,v in freq_n.items()},
        "missing_count": int((df["contact_count"] == "").sum())
    }
    
    return profile

def generate_issue_register(df: pd.DataFrame) -> pd.DataFrame:
    issues = []
    
    # Check case_id duplicates
    if df["case_id"].duplicated().any():
        issues.append({
            "issue_ID": "DQ-001",
            "field": "case_id",
            "issue_type": "duplicate identities",
            "description": "Exact matches found for case_id",
            "affected_raw_records": int(df["case_id"].duplicated(keep=False).sum()),
            "evidence": "case_id column contains duplicated string values",
            "proposed_future_action": "investigate and deduplicate in Phase 2",
            "current_phase": "Phase 1",
            "status": "confirmed"
        })
        
    # Dates formatting issues
    intake_slash_count = int(df['intake_date'].str.contains('/', na=False).sum())
    if intake_slash_count > 0:
        issues.append({
            "issue_ID": "DQ-002",
            "field": "intake_date",
            "issue_type": "mixed raw date representations",
            "description": "Dates contain slashes alongside dashes/other formats",
            "affected_raw_records": intake_slash_count,
            "evidence": f"Found {intake_slash_count} records with slashes",
            "proposed_future_action": "normalize in later phase",
            "current_phase": "Phase 1",
            "status": "confirmed"
        })
        
    # Category uncontrolled vocabulary
    categories_cnt = df["category"].nunique()
    if categories_cnt > 10:
        top_5 = df["category"].value_counts().head(5).index.tolist()
        non_top_5_count = int((~df["category"].isin(top_5)).sum())
        issues.append({
            "issue_ID": "DQ-003",
            "field": "category",
            "issue_type": "uncontrolled vocabulary",
            "description": "High number of distinct category representations (free text)",
            "affected_raw_records": non_top_5_count,
            "evidence": f"{categories_cnt} distinct raw values found. {non_top_5_count} records do not match top 5 variants.",
            "proposed_future_action": "mapping design in later phase",
            "current_phase": "Phase 1",
            "status": "confirmed"
        })
        
    # Missing priority
    missing_priority = int((df["priority"] == "").sum())
    if missing_priority > 0:
         issues.append({
            "issue_ID": "DQ-004",
            "field": "priority",
            "issue_type": "missing values",
            "description": "Priority field contains empty values",
            "affected_raw_records": missing_priority,
            "evidence": f"{missing_priority} empty strings detected",
            "proposed_future_action": "handle missingness logically in analysis",
            "current_phase": "Phase 1",
            "status": "confirmed"
        })
        
    return pd.DataFrame(issues)

if __name__ == "__main__":
    raw_path = "data/raw/case-export-2023-2025.csv"
    df = ingest_raw_data(raw_path)
    
    os.makedirs("outputs", exist_ok=True)
    
    profile = generate_profile(df)
    with open("outputs/baseline_profile.json", "w") as f:
        json.dump(profile, f, indent=4)
        
    issues_df = generate_issue_register(df)
    issues_df.to_csv("outputs/dq_issue_register.csv", index=False)
    
    print(f"Profiled {len(df)} rows and {len(df.columns)} columns.")
    print("Generated outputs/baseline_profile.json and outputs/dq_issue_register.csv")
