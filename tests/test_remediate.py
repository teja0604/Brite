import pytest
import pandas as pd
from dirty_data.anomaly import AnomalyType
from dirty_data.detect import detect_anomalies
from dirty_data.remediate import remediate_dataset, Disposition

def create_raw_df(data):
    columns = [
        "case_id", "client_ref", "district", "intake_date", 
        "closure_date", "status", "category", "priority", 
        "caseworker_id", "contact_count"
    ]
    rows = []
    for d in data:
        row = {
            "case_id": "CC-123", "client_ref": "John Doe", "district": "Calder Central", 
            "intake_date": "2023-01-01", "closure_date": "2023-02-01", "status": "Closed", 
            "category": "Standard", "priority": "High", "caseworker_id": "W123", 
            "contact_count": "3"
        }
        row.update(d)
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)

def run_pipeline(data):
    raw_df = create_raw_df(data)
    anomalies = detect_anomalies(raw_df)
    dicts = []
    if anomalies:
        for a in anomalies:
            d = a.__dict__.copy()
            d["anomaly_type"] = d["anomaly_type"].value
            d["severity"] = d["severity"].value
            dicts.append(d)
    anomalies_df = pd.DataFrame(dicts) if dicts else pd.DataFrame(columns=["source_row", "field", "anomaly_type", "severity", "reason", "observed_value", "normalized_signature"])
    return remediate_dataset(raw_df, anomalies_df)

# DATE TESTS
def test_canonical_date_remains_unchanged():
    clean, audit, qual = run_pipeline([{"intake_date": "2023-05-17"}])
    assert clean.iloc[0]["intake_date"] == "2023-05-17"
    # Unchanged canonical dates should NOT generate audit logs
    rule_audit = audit[(audit["field"] == "intake_date") & (audit["rule_id"] == "RULE-DATE-001")]
    assert len(rule_audit) == 0

def test_unambiguous_alternate_date_converts():
    clean, audit, qual = run_pipeline([{"intake_date": "May 17, 2024"}, {"intake_date": "13/04/2024"}])
    assert clean.iloc[0]["intake_date"] == "2024-05-17"
    assert clean.iloc[1]["intake_date"] == "2024-04-13"
    rule_audits = audit[audit["rule_id"] == "RULE-DATE-002"]
    assert len(rule_audits) == 2
    assert rule_audits.iloc[0]["disposition"] == Disposition.AUTO_REPAIR

def test_ambiguous_date_never_silently_converted():
    clean, audit, qual = run_pipeline([{"intake_date": "03/04/2024"}])
    assert clean.iloc[0]["intake_date"] == "03/04/2024" # untouched
    assert not qual.iloc[0]["eligible_for_duration_analysis"]
    rule_audit = audit[(audit["field"] == "intake_date") & (audit["rule_id"] == "RULE-DATE-003")]
    assert len(rule_audit) == 1
    assert rule_audit.iloc[0]["disposition"] == Disposition.UNRESOLVED

def test_invalid_date_never_fabricated():
    clean, audit, qual = run_pipeline([{"intake_date": "2024-02-30"}])
    assert clean.iloc[0]["intake_date"] == "2024-02-30" # untouched
    assert not qual.iloc[0]["eligible_for_duration_analysis"]
    rule_audit = audit[(audit["field"] == "intake_date") & (audit["rule_id"] == "RULE-DATE-004")]
    assert len(rule_audit) == 1
    assert rule_audit.iloc[0]["disposition"] == Disposition.UNRESOLVED

def test_temporal_contradiction_excluded():
    clean, audit, qual = run_pipeline([{"intake_date": "2023-05-01", "closure_date": "2023-04-01"}])
    assert clean.iloc[0]["intake_date"] == "2023-05-01"
    assert clean.iloc[0]["closure_date"] == "2023-04-01"
    assert not qual.iloc[0]["eligible_for_duration_analysis"]
    rule_audit = audit[audit["rule_id"] == "RULE-DATE-007"]
    assert len(rule_audit) == 1
    assert rule_audit.iloc[0]["disposition"] == Disposition.EXCLUDE_FROM_ANALYSIS

# IDENTITY TESTS
def test_exact_identical_duplicate_collapsed():
    row_data = {"case_id": "CC-123", "status": "Open"}
    clean, audit, qual = run_pipeline([row_data, row_data])
    assert len(clean) == 1
    assert clean.iloc[0]["source_row"] == 1 
    rule_audit = audit[audit["rule_id"] == "RULE-ID-001"]
    assert len(rule_audit) == 1
    assert rule_audit.iloc[0]["source_row"] == 2
    assert rule_audit.iloc[0]["disposition"] == Disposition.AUTO_REPAIR

def test_conflicting_duplicate_records_not_merged():
    clean, audit, qual = run_pipeline([
        {"case_id": "CC-123", "status": "Open"},
        {"case_id": "CC-123", "status": "Closed"}
    ])
    assert len(clean) == 2 # Both preserved
    
def test_candidate_identity_variants_not_merged():
    clean, audit, qual = run_pipeline([
        {"case_id": "CC-123"},
        {"case_id": "cc123"}
    ])
    assert len(clean) == 2
    assert "CANDIDATE_IDENTITY_VARIANT" in qual.iloc[0]["quality_flags"] or "CANDIDATE_IDENTITY_VARIANT" in qual.iloc[1]["quality_flags"]

# CATEGORY TESTS
def test_formatting_variants_normalize():
    clean, audit, qual = run_pipeline([{"category": "standard"}, {"category": " STANDARD "}])
    assert clean.iloc[0]["category"] == "Standard"
    assert clean.iloc[1]["category"] == "Standard"
    rule_audit = audit[audit["rule_id"] == "RULE-CAT-001"]
    assert len(rule_audit) == 2
    
def test_clean_category_no_audit_noise():
    clean, audit, qual = run_pipeline([{"category": "Standard"}])
    assert clean.iloc[0]["category"] == "Standard"
    # Should not generate a formatting normalization audit or UNCONTROLLED audit
    rule_audit = audit[audit["field"] == "category"]
    assert len(rule_audit) == 0

def test_unsupported_semantic_variants_flagged():
    clean, audit, qual = run_pipeline([{"category": "Standard Case"}, {"category": "Std."}]) 
    assert clean.iloc[0]["category"] == "Standard Case"
    assert clean.iloc[1]["category"] == "Std."
    # Since they aren't matching any known semantic, they are just ordinary distinct categories.
    # No formatting normalization or semantic resolution occurs, so no audit rows are generated.
    rule_audit = audit[audit["field"] == "category"]
    assert len(rule_audit) == 0
    
# MISSINGNESS
def test_expected_missing_closure_date():
    clean, audit, qual = run_pipeline([{"status": "Open", "closure_date": ""}])
    assert clean.iloc[0]["closure_date"] == ""
    assert qual.iloc[0]["eligible_for_duration_analysis"]
    # We stopped auditing expected missing values to reduce noise
    rule_audit = audit[audit["rule_id"] == "RULE-DATE-005"]
    assert len(rule_audit) == 0

def test_unexpected_missing_closure_date():
    clean, audit, qual = run_pipeline([{"status": "Closed", "closure_date": ""}])
    assert not qual.iloc[0]["eligible_for_duration_analysis"]
    rule_audit = audit[audit["rule_id"] == "RULE-DATE-006"]
    assert len(rule_audit) == 1

def test_missing_priority():
    clean, audit, qual = run_pipeline([{"priority": ""}])
    assert clean.iloc[0]["priority"] == ""
    rule_audit = audit[audit["rule_id"] == "RULE-MISS-001"]
    assert len(rule_audit) == 1

# NUMERIC
def test_invalid_contact_count():
    clean, audit, qual = run_pipeline([{"contact_count": "invalid"}])
    assert clean.iloc[0]["contact_count"] == "invalid"
    assert not qual.iloc[0]["eligible_for_case_counts"]
    rule_audit = audit[audit["rule_id"] == "RULE-NUM-001"]
    assert len(rule_audit) == 1

# PROVENANCE & AUDIT & RECORD STATUS
def test_provenance_and_audit():
    clean, audit, qual = run_pipeline([{"intake_date": "2024-05-17", "closure_date": "2023-01-01"}])
    assert clean.iloc[0]["source_row"] == 1
    assert qual.iloc[0]["source_row"] == 1
    # EXCLUDE_FROM_ANALYSIS (temporal contradiction)
    assert qual.iloc[0]["record_status"] == Disposition.EXCLUDE_FROM_ANALYSIS
    
def test_clean_record_status():
    # Provide fully valid row
    clean, audit, qual = run_pipeline([{"intake_date": "2024-01-01", "closure_date": "2024-02-01", "status": "Closed", "category": "Standard", "priority": "High", "contact_count": "1"}])
    assert qual.iloc[0]["record_status"] == "CLEAN"
