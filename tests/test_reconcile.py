import pandas as pd
import pytest
from dirty_data.reconcile import reconcile_dataset

def test_reconcile_exact_match():
    aligned_df = pd.DataFrame({
        "case_id": ["C1", "C1"],
        "source_system": ["ORIGINAL", "SUPPLEMENTARY"],
        "source_row_index": [10, 20],
        "client_ref": ["Ref1", ""],
        "extract_date": ["", "2026-01-14"]
    })
    
    idx_df = pd.DataFrame({
        "case_id": ["C1"],
        "cardinality": ["ONE_TO_ONE"],
        "match_status": ["MATCHED"]
    })
    
    comp_df = pd.DataFrame([{
        "case_id": "C1",
        "original_source_row": 10,
        "supplementary_source_row": 20,
        "field_name": "district",
        "original_value": "Northgate",
        "supplementary_value": "Northgate",
        "original_presence": "PRESENT",
        "supplementary_presence": "PRESENT",
        "comparison_result": "EXACT_MATCH"
    }])
    
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    
    assert len(recon_df) == 1
    assert recon_df.iloc[0]["district"] == "Northgate"
    assert recon_df.iloc[0]["reconciliation_status"] == "CLEAN"
    
    assert len(audit_df) == 1
    assert audit_df.iloc[0]["rule_applied"] == "RULE-S5-MATCH"

def test_reconcile_rep_equivalent():
    aligned_df = pd.DataFrame({
        "case_id": ["C1", "C1"],
        "source_system": ["ORIGINAL", "SUPPLEMENTARY"],
        "source_row_index": [10, 20],
        "client_ref": ["Ref1", ""],
        "extract_date": ["", "2026-01-14"]
    })
    idx_df = pd.DataFrame({"case_id": ["C1"], "cardinality": ["ONE_TO_ONE"], "match_status": ["MATCHED"]})
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": "intake_date",
        "original_value": "May 17, 2024", "supplementary_value": "2024-05-17",
        "original_presence": "PRESENT", "supplementary_presence": "PRESENT",
        "comparison_result": "REPRESENTATION_EQUIVALENT"
    }])
    
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    
    assert recon_df.iloc[0]["intake_date"] == "May 17, 2024"  # Default original formatting
    assert audit_df.iloc[0]["rule_applied"] == "RULE-S5-REP-EQUIV"

def test_reconcile_missing_imputation():
    aligned_df = pd.DataFrame({
        "case_id": ["C1", "C1"],
        "source_system": ["ORIGINAL", "SUPPLEMENTARY"],
        "source_row_index": [10, 20],
        "client_ref": ["Ref1", ""],
        "extract_date": ["", "2026-01-14"]
    })
    idx_df = pd.DataFrame({"case_id": ["C1"], "cardinality": ["ONE_TO_ONE"], "match_status": ["MATCHED"]})
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": "priority",
        "original_value": "", "supplementary_value": "High",
        "original_presence": "MISSING", "supplementary_presence": "PRESENT",
        "comparison_result": "MISSING_ONE_SIDE"
    }])
    
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    
    assert recon_df.iloc[0]["priority"] == "High"
    assert audit_df.iloc[0]["rule_applied"] == "RULE-S5-IMPUTE"

def test_reconcile_unavailable_one_side():
    aligned_df = pd.DataFrame({
        "case_id": ["C1", "C1"],
        "source_system": ["ORIGINAL", "SUPPLEMENTARY"],
        "source_row_index": [10, 20],
        "client_ref": ["Ref1", ""],
        "extract_date": ["", "2026-01-14"]
    })
    idx_df = pd.DataFrame({"case_id": ["C1"], "cardinality": ["ONE_TO_ONE"], "match_status": ["MATCHED"]})
    comp_df = pd.DataFrame([{
        "case_id": "C1", "original_source_row": 10, "supplementary_source_row": 20, "field_name": "contact_count",
        "original_value": "5", "supplementary_value": "",
        "original_presence": "PRESENT", "supplementary_presence": "UNAVAILABLE",
        "comparison_result": "UNAVAILABLE_ONE_SIDE"
    }])
    
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    
    assert recon_df.iloc[0]["contact_count"] == "5"
    assert audit_df.iloc[0]["rule_applied"] == "RULE-S5-UNAVAILABLE"

def test_reconcile_original_only():
    aligned_df = pd.DataFrame({
        "case_id": ["C2"],
        "source_system": ["ORIGINAL"],
        "client_ref": ["Ref2"],
        "extract_date": [""],
        "district": ["Weybridge"]
    })
    idx_df = pd.DataFrame({"case_id": ["C2"], "cardinality": ["ORIGINAL_ONLY"], "match_status": ["ORIGINAL_ONLY"]})
    comp_df = pd.DataFrame([{
        "case_id": "C2", "field_name": "ALL",
        "original_value": "", "supplementary_value": "",
        "original_presence": "UNAVAILABLE", "supplementary_presence": "UNAVAILABLE",
        "comparison_result": "NOT_COMPARABLE"
    }])
    
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert len(recon_df) == 1
    assert recon_df.iloc[0]["district"] == "Weybridge"
    assert recon_df.iloc[0]["reconciliation_status"] == "ORIGINAL_ONLY"

def test_reconcile_conflict():
    aligned_df = pd.DataFrame({
        'case_id': ['C3', 'C3'],
        'source_system': ['ORIGINAL', 'SUPPLEMENTARY'],
        'source_row_index': [10, 20],
        'client_ref': ['Ref3', ''],
        'extract_date': ['', '2026-01-14']
    })
    idx_df = pd.DataFrame({'case_id': ['C3'], 'cardinality': ['ONE_TO_ONE'], 'match_status': ['MATCHED']})
    comp_df = pd.DataFrame([
        {
            'case_id': 'C3', 'original_source_row': 10, 'supplementary_source_row': 20, 'field_name': 'status',
            'original_value': 'Open', 'supplementary_value': 'Closed',
            'original_presence': 'PRESENT', 'supplementary_presence': 'PRESENT',
            'comparison_result': 'CONFLICT'
        },
        {
            'case_id': 'C3', 'original_source_row': 10, 'supplementary_source_row': 20, 'field_name': 'district',
            'original_value': 'D1', 'supplementary_value': 'D2',
            'original_presence': 'PRESENT', 'supplementary_presence': 'PRESENT',
            'comparison_result': 'CONFLICT'
        }
    ])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert len(recon_df) == 1
    assert recon_df.iloc[0]['status'] == 'Closed' # Supplementary wins for status
    assert recon_df.iloc[0]['district'] == 'D1'   # Original wins for district
    assert recon_df.iloc[0]['reconciliation_status'] == 'CONFLICT'

def test_reconcile_multi_record():
    aligned_df = pd.DataFrame({
        'case_id': ['C4', 'C4', 'C4'],
        'source_system': ['ORIGINAL', 'ORIGINAL', 'SUPPLEMENTARY'],
        'source_row_index': [1, 2, 3],
        'client_ref': ['Ref4', 'Ref4', ''],
        'extract_date': ['', '', '2026-01-14']
    })
    idx_df = pd.DataFrame({'case_id': ['C4'], 'cardinality': ['MANY_TO_ONE'], 'match_status': ['MATCHED']})
    comp_df = pd.DataFrame([
        {
            'case_id': 'C4', 'original_source_row': 1, 'supplementary_source_row': 3, 'field_name': 'status',
            'original_value': 'Open', 'supplementary_value': 'Open',
            'original_presence': 'PRESENT', 'supplementary_presence': 'PRESENT',
            'comparison_result': 'EXACT_MATCH'
        },
        {
            'case_id': 'C4', 'original_source_row': 2, 'supplementary_source_row': 3, 'field_name': 'status',
            'original_value': 'Open', 'supplementary_value': 'Open',
            'original_presence': 'PRESENT', 'supplementary_presence': 'PRESENT',
            'comparison_result': 'EXACT_MATCH'
        }
    ])
    recon_df, audit_df = reconcile_dataset(aligned_df, idx_df, comp_df)
    assert len(recon_df) == 2 # 2 reconciled records preserved (one for each original row)
    assert len(audit_df) == 2

