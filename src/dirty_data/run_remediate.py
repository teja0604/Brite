import pandas as pd
import os
from dirty_data.detect import detect_anomalies
from dirty_data.remediate import remediate_dataset
from dirty_data.anomaly import AnomalyType

def run_pipeline():
    print("Loading raw dataset...")
    raw_df = pd.read_csv("data/raw/case-export-2023-2025.csv", dtype=str, keep_default_na=False)
    
    print("Running Phase 2 anomaly detection...")
    anomalies = detect_anomalies(raw_df)
    dicts = []
    if anomalies:
        for a in anomalies:
            d = a.__dict__.copy()
            d["anomaly_type"] = d["anomaly_type"].value
            d["severity"] = d["severity"].value
            dicts.append(d)
    anomalies_df = pd.DataFrame(dicts) if dicts else pd.DataFrame(columns=["source_row", "field", "anomaly_type", "severity", "reason", "observed_value", "normalized_signature"])
    
    print("Running Phase 3 remediation...")
    clean_df, audit_df, qual_df = remediate_dataset(raw_df, anomalies_df)
    
    os.makedirs("outputs", exist_ok=True)
    
    clean_df.to_csv("outputs/cleaned_cases.csv", index=False)
    audit_df.to_csv("outputs/cleaning_audit.csv", index=False)
    qual_df.to_csv("outputs/record_quality.csv", index=False)
    
    print("\n--- RECONCILIATION ---")
    raw_count = len(raw_df)
    clean_count = len(clean_df)
    dropped_exact_dups = len(audit_df[audit_df["rule_id"] == "RULE-ID-001"])
    print(f"Raw Source Rows: {raw_count}")
    print(f"Cleaned Rows: {clean_count}")
    print(f"Dropped Exact Dups: {dropped_exact_dups}")
    if raw_count == clean_count + dropped_exact_dups:
        print("Reconciliation SUCCESS")
    else:
        print("Reconciliation FAILED")
        
    print("\n--- ACTION-LEVEL DISPOSITIONS (Audit rows) ---")
    if not audit_df.empty:
        print(audit_df["disposition"].value_counts())
    
    print("\n--- RECORD-LEVEL STATUS (Unique rows) ---")
    if not qual_df.empty:
        print(qual_df["record_status"].value_counts())
    
    print("\n--- ELIGIBILITY EXCLUSIONS ---")
    duration_exclusions = len(qual_df[qual_df["eligible_for_duration_analysis"] == False])
    counts_exclusions = len(qual_df[qual_df["eligible_for_case_counts"] == False])
    print(f"Excluded from duration analysis: {duration_exclusions}")
    print(f"Excluded from case counts: {counts_exclusions}")

if __name__ == "__main__":
    run_pipeline()
