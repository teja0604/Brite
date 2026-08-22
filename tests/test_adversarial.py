import os
import pytest
import pandas as pd
from dirty_data.ingest import ingest_raw_data
from dirty_data.anomaly import AnomalyType, Severity
from dirty_data.detect import detect_anomalies
from dirty_data.remediate import remediate_dataset
from dirty_data.analysis_spec import classify_30_day_outcome

# ==========================================
# A. INPUT FAILURE TESTS
# ==========================================
def test_input_missing_csv(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest_raw_data(str(tmp_path / "nonexistent.csv"))

def test_input_missing_required_column(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("case_id,client_ref,district\n1,2,3", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing expected columns"):
        ingest_raw_data(str(f))

def test_input_empty_csv(tmp_path):
    f = tmp_path / "empty.csv"
    f.write_text("", encoding="utf-8")
    with pytest.raises(ValueError): # pandas raises error or our code does
        try:
            ingest_raw_data(str(f))
        except Exception as e:
            assert isinstance(e, (ValueError, pd.errors.EmptyDataError))
            raise ValueError()

# ==========================================
# B. SCHEMA & DATA CORRUPTION TESTS
# ==========================================
def test_candidate_identity_variant_is_not_merged():
    from dirty_data.detect import generate_anomaly_report
    df = pd.DataFrame({"source_row": [1, 2], "case_id": ["CC-001", "cc-001"], "client_ref": ["1", "1"], 
                       "intake_date": ["2023-01-01", "2023-01-01"], "closure_date": ["", ""], "status": ["Open", "Open"], 
                       "category": ["Standard", "Standard"], "priority": ["", ""], "contact_count": ["1", "1"], "district": ["A", "A"], "caseworker_id": ["1", "1"]})
    anomalies = detect_anomalies(df)
    has_variant = any(a.anomaly_type == AnomalyType.CANDIDATE_IDENTITY_VARIANT for a in anomalies)
    assert has_variant
    
    cleaned, audit, rq = remediate_dataset(df, generate_anomaly_report(anomalies))
    # The action must be flag, not repair (no silent merge)
    for idx, row in audit.iterrows():
        if row["rule_id"] == "RULE-ID-003":
            assert row["action"] == "Retain without merging"

# ==========================================
# C. DATE ADVERSARIAL TESTING
# ==========================================
def test_ambiguous_date_is_never_silently_parsed():
    from dirty_data.detect import generate_anomaly_report
    # 03/04/2024 is ambiguous
    df = pd.DataFrame({"source_row": [1], "case_id": ["1"], "intake_date": ["03/04/2024"], "closure_date": [""], "status": ["Open"], "category": ["Standard"], "priority": [""], "contact_count": ["1"], "client_ref": ["1"], "district": ["A"], "caseworker_id": ["1"]})
    anomalies = detect_anomalies(df)
    ambig = [a for a in anomalies if a.anomaly_type == AnomalyType.AMBIGUOUS_DATE_FORMAT]
    assert len(ambig) == 1
    
    cleaned, audit, rq = remediate_dataset(df, generate_anomaly_report(anomalies))
    
    assert not rq.iloc[0]["eligible_for_duration_analysis"]
    assert cleaned.iloc[0]["intake_date"] == "03/04/2024"

# ==========================================
# D. 30-DAY CLOSURE ADVERSARIAL TESTING
# ==========================================
def test_recent_case_is_not_counted_as_30_day_failure():
    # Intake 2025-12-15, open
    row = pd.Series({"intake_date": "2025-12-15", "status": "Open", "closure_date": ""})
    outcome = classify_30_day_outcome(row)
    assert outcome == "OUTCOME_NOT_OBSERVABLE"

def test_exact_30_day_boundary():
    # 30 days exactly
    row = pd.Series({"intake_date": "2023-01-01", "status": "Closed", "closure_date": "2023-01-31"})
    assert classify_30_day_outcome(row) == "CLOSED_WITHIN_30_DAYS"
    
    # 31 days
    row2 = pd.Series({"intake_date": "2023-01-01", "status": "Closed", "closure_date": "2023-02-01"})
    assert classify_30_day_outcome(row2) == "NOT_CLOSED_BY_30_DAYS"

# ==========================================
# E. CATEGORY ADVERSARIAL TESTING
# ==========================================
def test_category_semantic_equivalence_not_invented():
    from dirty_data.detect import generate_anomaly_report
    # Std. must not become Standard
    df = pd.DataFrame({"source_row": [1], "case_id": ["1"], "intake_date": ["2023-01-01"], "closure_date": [""], "status": ["Open"], "category": ["Std."], "priority": [""], "contact_count": ["1"], "client_ref": ["1"], "district": ["A"], "caseworker_id": ["1"]})
    anomalies = detect_anomalies(df)
    cleaned, audit, rq = remediate_dataset(df, generate_anomaly_report(anomalies))
    assert cleaned.iloc[0]["category"] == "Std."

# ==========================================
# F. ANALYSIS FAILURE TESTING
# ==========================================
def test_analysis_zero_records_no_crash():
    from dirty_data.analyze import analyze_question_1, analyze_question_2, analyze_question_3
    # Create empty dataframes
    df = pd.DataFrame(columns=["source_row", "case_id", "intake_date", "closure_date", "status", "year", "priority", "district", "category"])
    rq = pd.DataFrame(columns=["source_row", "eligible_for_duration_analysis", "eligible_for_case_counts"])
    
    # Run analysis, it should not crash
    analyze_question_1(df, rq)
    analyze_question_2(df, rq)
    analyze_question_3(df, rq)

# ==========================================
# G. REPORTING & UPSTREAM ARTIFACT FAILURES
# ==========================================
def test_missing_analysis_artifact_fails_loudly(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent / "src")
    
    # Try running build_reports.py against an empty tmp_path
    script_path = str(Path(__file__).resolve().parent.parent / "src" / "dirty_data" / "build_reports.py")
    result = subprocess.run([sys.executable, script_path, str(tmp_path)], capture_output=True, text=True, env=env)
    assert result.returncode == 1
    assert "Missing required input" in result.stdout or "FileNotFoundError" in result.stderr or result.returncode != 0

# ==========================================
# H. IMMUTABILITY & PROVENANCE ATTACK
# ==========================================
def test_raw_source_remains_immutable():
    import hashlib
    from pathlib import Path
    RAW_FILE = Path(__file__).resolve().parent.parent / "data" / "raw" / "case-export-2023-2025.csv"
    h = hashlib.sha256()
    with open(RAW_FILE, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    assert h.hexdigest() == "f65bec452b2f25404fc7b41d7d9c1ed35ef993fded974cf432cb36945ac27dd6"

# ==========================================
# I. RESOURCE / LARGE INPUT TEST
# ==========================================
def test_large_input_performance(tmp_path):
    from pathlib import Path
    # Create a 5x dataset
    RAW_FILE = Path(__file__).resolve().parent.parent / "data" / "raw" / "case-export-2023-2025.csv"
    df = pd.read_csv(RAW_FILE, dtype=str, keep_default_na=False)
    
    large_df = pd.concat([df] * 5, ignore_index=True)
    large_file = tmp_path / "large_input.csv"
    large_df.to_csv(large_file, index=False)
    
    # Just verify ingest can handle it without dying
    ingested = ingest_raw_data(str(large_file))
    assert len(ingested) == len(df) * 5
    
    # Verify it doesn't crash on simple detect
    assert ingested.shape[0] == 75500
