import pandas as pd
import pytest
from dirty_data.reconcile import reconcile_dataset

def create_base_data(case_id="C1", match_status="MATCHED", cardinality="ONE_TO_ONE", o_idx=10, s_idx=20):
    aligned_df = pd.DataFrame({
        "case_id": [case_id, case_id],
        "source_system": ["ORIGINAL", "SUPPLEMENTARY"],
        "source_row_index": [o_idx, s_idx],
        "client_ref": ["Ref1", "Ref2"],
        "extract_date": ["", "2026-01-14"]
    })
    idx_df = pd.DataFrame({
        "case_id": [case_id],
        "cardinality": [cardinality],
        "match_status": [match_status]
    })
    return aligned_df, idx_df

def test_1_exact_match():
    aligned_df, idx_df = create_base_data()
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": "category",
        "original_value": "A", "supplementary_value": "A",
        "original_presence": "PRESENT", "supplementary_presence": "PRESENT",
        "comparison_result": "EXACT_MATCH"
    }])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert recon_df.iloc[0]["category"] == "A"
    assert "RULE-S5-MATCH" in audit_df["rule_applied"].values

def test_2_representation_equivalent():
    aligned_df, idx_df = create_base_data()
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": "intake_date",
        "original_value": "01/01/2026", "supplementary_value": "2026-01-01",
        "original_presence": "PRESENT", "supplementary_presence": "PRESENT",
        "comparison_result": "REPRESENTATION_EQUIVALENT"
    }])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert recon_df.iloc[0]["intake_date"] == "01/01/2026"  # Keep Original format
    assert "RULE-S5-REP-EQUIV" in audit_df["rule_applied"].values

def test_3_missing_one_side():
    aligned_df, idx_df = create_base_data()
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": "priority",
        "original_value": "", "supplementary_value": "High",
        "original_presence": "MISSING", "supplementary_presence": "PRESENT",
        "comparison_result": "MISSING_ONE_SIDE"
    }])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert recon_df.iloc[0]["priority"] == "High"
    assert "RULE-S5-IMPUTE" in audit_df["rule_applied"].values

def test_4_unavailable_one_side():
    aligned_df, idx_df = create_base_data()
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": "contact_count",
        "original_value": "3", "supplementary_value": "",
        "original_presence": "PRESENT", "supplementary_presence": "UNAVAILABLE",
        "comparison_result": "UNAVAILABLE_ONE_SIDE"
    }])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert recon_df.iloc[0]["contact_count"] == "3"
    assert "RULE-S5-UNAVAILABLE" in audit_df["rule_applied"].values

def test_5_to_13_conflict_precedence():
    aligned_df, idx_df = create_base_data()
    # 5. status conflict -> SUPPLEMENTARY
    # 6. closure_date conflict -> SUPPLEMENTARY
    # 7-13. others -> ORIGINAL
    fields = [
        ("status", "SUPPLEMENTARY"),
        ("closure_date", "SUPPLEMENTARY"),
        ("district", "ORIGINAL"),
        ("intake_date", "ORIGINAL"),
        ("category", "ORIGINAL"),
        ("priority", "ORIGINAL"),
        ("caseworker_id", "ORIGINAL"),
        ("contact_count", "ORIGINAL")
    ]
    
    comp_rows = []
    for f, _ in fields:
        comp_rows.append({
            "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": f,
            "original_value": "O_VAL", "supplementary_value": "S_VAL",
            "original_presence": "PRESENT", "supplementary_presence": "PRESENT",
            "comparison_result": "CONFLICT"
        })
        
    comp_df = pd.DataFrame(comp_rows)
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    
    for f, expected_winner in fields:
        expected_val = "S_VAL" if expected_winner == "SUPPLEMENTARY" else "O_VAL"
        assert recon_df.iloc[0][f] == expected_val

def test_14_extract_date_provenance():
    aligned_df, idx_df = create_base_data()
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": "category",
        "original_value": "A", "supplementary_value": "A",
        "original_presence": "PRESENT", "supplementary_presence": "PRESENT",
        "comparison_result": "EXACT_MATCH"
    }])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert recon_df.iloc[0]["extract_date"] == "" # Original has no extract date
    
    extract_audit = audit_df[audit_df["field"] == "extract_date"].iloc[0]
    assert extract_audit["original_value"] == ""
    assert extract_audit["supplementary_value"] == "2026-01-14"
    assert extract_audit["comparison_result"] == "PROVENANCE_ONLY"
    assert extract_audit["reconciliation_decision"] == "RETAIN_PROVENANCE"

def test_15_16_many_to_one_preservation():
    aligned_df = pd.DataFrame({
        "case_id": ["C1", "C1", "C1"],
        "source_system": ["ORIGINAL", "ORIGINAL", "SUPPLEMENTARY"],
        "source_row_index": [1, 2, 3],
        "client_ref": ["Ref1A", "Ref1B", ""],
        "extract_date": ["", "", "2026-01-14"]
    })
    idx_df = pd.DataFrame({"case_id": ["C1"], "cardinality": ["MANY_TO_ONE"], "match_status": ["MATCHED"]})
    comp_df = pd.DataFrame([
        {
            "case_id": "C1", "original_source_row": 1, "supplementary_source_row": 3, "field_name": "status",
            "original_value": "Open", "supplementary_value": "Closed",
            "original_presence": "PRESENT", "supplementary_presence": "PRESENT",
            "comparison_result": "CONFLICT"
        },
        {
            "case_id": "C1", "original_source_row": 2, "supplementary_source_row": 3, "field_name": "status",
            "original_value": "Pending", "supplementary_value": "Closed",
            "original_presence": "PRESENT", "supplementary_presence": "PRESENT",
            "comparison_result": "CONFLICT"
        }
    ])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert len(recon_df) == 2 # Preserves both original rows
    
    # 17. Deterministic
    assert recon_df.iloc[0]["status"] == "Closed" # Supplementary wins
    assert recon_df.iloc[1]["status"] == "Closed"
    assert recon_df.iloc[0]["client_ref"] == "Ref1A"
    assert recon_df.iloc[1]["client_ref"] == "Ref1B"

def test_18_audit_provenance():
    aligned_df, idx_df = create_base_data(o_idx=99, s_idx=100)
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 99, "supplementary_source_row": 100, "field_name": "priority",
        "original_value": "", "supplementary_value": "High",
        "original_presence": "MISSING", "supplementary_presence": "PRESENT",
        "comparison_result": "MISSING_ONE_SIDE"
    }])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    
    audit_row = audit_df[audit_df["field"] == "priority"].iloc[0]
    assert audit_row["original_source_row"] == 99
    assert audit_row["supplementary_source_row"] == 100

def test_19_one_to_many_unresolved():
    aligned_df, idx_df = create_base_data(cardinality="ONE_TO_MANY")
    comp_df = pd.DataFrame(columns=["case_id", "original_source_row", "supplementary_source_row", "field_name", "original_value", "supplementary_value", "original_presence", "supplementary_presence", "comparison_result"]) # Doesn't matter, should be skipped
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert len(recon_df) == 0
    assert audit_df.iloc[0]["reconciliation_decision"] == "UNRESOLVED_MULTI_RECORD"

def test_20_no_silent_record_loss():
    aligned_df = pd.DataFrame({
        "case_id": ["C1"],
        "source_system": ["ORIGINAL"],
        "source_row_index": [5],
        "client_ref": [""],
        "extract_date": [""]
    })
    idx_df = pd.DataFrame({"case_id": ["C1"], "cardinality": ["ORIGINAL_ONLY"], "match_status": ["ORIGINAL_ONLY"]})
    comp_df = pd.DataFrame(columns=["case_id", "original_source_row", "supplementary_source_row", "field_name", "original_value", "supplementary_value", "original_presence", "supplementary_presence", "comparison_result"])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert len(recon_df) == 1
    assert recon_df.iloc[0]["reconciliation_status"] == "ORIGINAL_ONLY"
