import pytest
import pandas as pd
from dirty_data.anomaly import AnomalyType, Severity
from dirty_data.detect import detect_anomalies, generate_anomaly_report
from dirty_data.contract import analyze_date_format, normalize_string_signature

def create_df(data):
    columns = [
        "case_id", "client_ref", "district", "intake_date", 
        "closure_date", "status", "category", "priority", 
        "caseworker_id", "contact_count"
    ]
    rows = []
    for d in data:
        row = {
            "case_id": "CC-123", "client_ref": "John Doe", "district": "Calder Central", 
            "intake_date": "2023-01-01", "closure_date": "", "status": "Open", 
            "category": "Standard", "priority": "High", "caseworker_id": "W123", 
            "contact_count": "3"
        }
        row.update(d)
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)

def test_normal_case():
    df = create_df([{}])
    anomalies = detect_anomalies(df)
    assert len(anomalies) == 0

def test_missing_values():
    df = create_df([{"case_id": "", "district": "", "status": ""}])
    anomalies = detect_anomalies(df)
    types = [(a.field, a.anomaly_type) for a in anomalies]
    assert ("case_id", AnomalyType.MISSING_VALUE) in types
    assert ("district", AnomalyType.MISSING_VALUE) in types
    assert ("status", AnomalyType.MISSING_VALUE) in types

# IDENTITY TESTS
def test_exact_duplicate_case_id():
    df = create_df([{"case_id": "CC-123"}, {"case_id": "CC-123"}])
    anomalies = detect_anomalies(df)
    exact_dups = [a for a in anomalies if a.anomaly_type == AnomalyType.EXACT_DUPLICATE]
    assert len(exact_dups) == 2 # both rows flagged
    assert exact_dups[0].source_row == 1
    assert exact_dups[1].source_row == 2
    
def test_candidate_identity_variant():
    df = create_df([{"case_id": "CC-123"}, {"case_id": "cc123"}])
    anomalies = detect_anomalies(df)
    variants = [a for a in anomalies if a.anomaly_type == AnomalyType.CANDIDATE_IDENTITY_VARIANT]
    assert len(variants) == 2
    assert variants[0].observed_value == "CC-123"
    assert variants[1].observed_value == "cc123"
    assert variants[0].normalized_signature == "cc123"

# CATEGORY TESTS
def test_rare_category_not_flagged():
    df = create_df([{"category": "rare_but_valid", "case_id": "CC-1"}, {"category": "other", "case_id": "CC-2"}])
    anomalies = detect_anomalies(df)
    cat_anomalies = [a for a in anomalies if a.field == "category"]
    assert len(cat_anomalies) == 0 # no variants

def test_candidate_category_variant():
    df = create_df([{"category": "Standard", "case_id": "CC-1"}, {"category": "standard ", "case_id": "CC-2"}])
    anomalies = detect_anomalies(df)
    variants = [a for a in anomalies if a.anomaly_type == AnomalyType.CANDIDATE_CATEGORY_VARIANT]
    assert len(variants) == 2
    assert variants[0].normalized_signature == "standard"
    
# DATE TESTS
def test_valid_iso_date_passes():
    # 2024 is a leap year
    df = create_df([{"intake_date": "2024-02-29"}])
    anomalies = detect_anomalies(df)
    assert not any(a.field == "intake_date" for a in anomalies)

def test_alternate_date_format():
    df = create_df([{"intake_date": "May 17, 2024"}])
    anomalies = detect_anomalies(df)
    date_vars = [a for a in anomalies if a.anomaly_type == AnomalyType.DATE_FORMAT_VARIATION]
    assert len(date_vars) == 1
    assert date_vars[0].observed_value == "May 17, 2024"
    
def test_ambiguous_date_formats():
    # Both numbers <= 12
    df = create_df([{"intake_date": "03/04/2024"}, {"intake_date": "11/12/2024"}])
    anomalies = detect_anomalies(df)
    ambiguous = [a for a in anomalies if a.anomaly_type == AnomalyType.AMBIGUOUS_DATE_FORMAT]
    assert len(ambiguous) == 2
    assert ambiguous[0].observed_value == "03/04/2024"
    assert ambiguous[1].observed_value == "11/12/2024"

def test_unambiguous_numeric_date():
    # 13 cannot be a month, so they are unambiguous
    df = create_df([{"intake_date": "13/04/2024"}, {"intake_date": "04/13/2024"}])
    anomalies = detect_anomalies(df)
    # Should not be AMBIGUOUS_DATE_FORMAT, should be DATE_FORMAT_VARIATION
    vars = [a for a in anomalies if a.anomaly_type == AnomalyType.DATE_FORMAT_VARIATION]
    assert len(vars) == 2
    ambig = [a for a in anomalies if a.anomaly_type == AnomalyType.AMBIGUOUS_DATE_FORMAT]
    assert len(ambig) == 0
    assert vars[0].observed_value == "13/04/2024"
    assert vars[1].observed_value == "04/13/2024"
    
def test_invalid_date():
    # Various invalid dates
    df = create_df([
        {"intake_date": "2023-99-99"},
        {"intake_date": "2023-02-29"}, # not a leap year
        {"intake_date": "2024-02-30"}  # 30 days in feb is invalid even in leap year
    ])
    anomalies = detect_anomalies(df)
    inv_dates = [a for a in anomalies if a.anomaly_type == AnomalyType.INVALID_DATE]
    assert len(inv_dates) == 3
    
def test_empty_date_produces_missing_value():
    df = create_df([{"status": "Closed", "closure_date": ""}])
    anomalies = detect_anomalies(df)
    missing = [a for a in anomalies if a.anomaly_type == AnomalyType.MISSING_VALUE and a.field == "closure_date"]
    assert len(missing) == 1
    
def test_temporal_contradiction_requires_unambiguous():
    # Ambiguous dates don't trigger temporal contradiction to avoid false positives
    df = create_df([{"intake_date": "05/01/2023", "closure_date": "04/01/2023", "status": "Closed"}])
    anomalies = detect_anomalies(df)
    contras = [a for a in anomalies if a.anomaly_type == AnomalyType.LOGICAL_CONTRADICTION and a.field == "closure_date"]
    assert len(contras) == 0
    
    # Valid but variant format does not trigger it either
    df2 = create_df([{"intake_date": "May 1, 2023", "closure_date": "April 1, 2023", "status": "Closed"}])
    anomalies2 = detect_anomalies(df2)
    contras2 = [a for a in anomalies2 if a.anomaly_type == AnomalyType.LOGICAL_CONTRADICTION and a.field == "closure_date"]
    assert len(contras2) == 0
    
    # Canonical dates do trigger it
    df3 = create_df([{"intake_date": "2023-05-01", "closure_date": "2023-04-01", "status": "Closed"}])
    anomalies3 = detect_anomalies(df3)
    contras3 = [a for a in anomalies3 if a.anomaly_type == AnomalyType.LOGICAL_CONTRADICTION and a.field == "closure_date"]
    assert len(contras3) == 1

# EVIDENCE TESTS
def test_evidence_fields_preserved():
    df = create_df([{"case_id": "CC-123"}, {"case_id": "cc123"}])
    anomalies = detect_anomalies(df)
    a = anomalies[0]
    assert a.source_row in (1, 2)
    assert a.observed_value in ("CC-123", "cc123")
    assert a.normalized_signature == "cc123"

def test_generate_report_deterministic():
    df = create_df([{"district": "Fake1"}, {"district": "Fake2"}])
    report1 = generate_anomaly_report(detect_anomalies(df))
    report2 = generate_anomaly_report(detect_anomalies(df))
    assert report1.equals(report2)
