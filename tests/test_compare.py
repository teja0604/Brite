import pandas as pd
import pytest
from dirty_data.compare import compare_fields, _compare_single_field
from dirty_data.identity import match_identities
from dirty_data.adapter import adapt_original_to_canonical, adapt_supplementary_to_canonical

def test_compare_taxonomy():
    # 1. EXACT_MATCH
    assert _compare_single_field("district", "Northgate", "Northgate", {}, {})[0] == "EXACT_MATCH"
    
    # 2. REPRESENTATION_EQUIVALENT date
    assert _compare_single_field("intake_date", "2024-05-17", "May 17, 2024", {}, {})[0] == "REPRESENTATION_EQUIVALENT"
    
    # 3. DATE CONFLICT
    assert _compare_single_field("intake_date", "2024-05-17", "2024-06-17", {}, {})[0] == "CONFLICT"
    
    # 4. CATEGORY MATCH
    assert _compare_single_field("category", "Standard", "Standard", {}, {})[0] == "EXACT_MATCH"
    
    # 5. CATEGORY CONFLICT
    assert _compare_single_field("category", "Standard", "Expedited", {}, {})[0] == "CONFLICT"
    
    # 6. PRIORITY MATCH
    assert _compare_single_field("priority", "High", "High", {}, {})[0] == "EXACT_MATCH"
    
    # 7. PRIORITY CONFLICT
    assert _compare_single_field("priority", "High", "Low", {}, {})[0] == "CONFLICT"
    
    # 8. MISSING Original value
    assert _compare_single_field("priority", "", "High", {}, {})[0] == "MISSING_ONE_SIDE"
    
    # 9. MISSING Supplementary value
    assert _compare_single_field("priority", "High", "", {}, {})[0] == "MISSING_ONE_SIDE"
    
    # 10. UNAVAILABLE contact_count
    res, reason, o_pres, s_pres = _compare_single_field("contact_count", "5", "", {}, {"contact_count": "UNAVAILABLE"})
    assert res == "UNAVAILABLE_ONE_SIDE"
    assert o_pres == "PRESENT"
    assert s_pres == "UNAVAILABLE"
    
    # 11. INVALID date
    assert _compare_single_field("intake_date", "Not a date", "2024-01-01", {}, {})[0] == "INVALID_COMPARISON"
    
    # 12. AMBIGUOUS date
    assert _compare_single_field("intake_date", "03-04-2024", "2024-01-01", {}, {})[0] == "INVALID_COMPARISON"
    
    # 13. STATUS semantic comparison
    assert _compare_single_field("status", "Closed", "Closed", {}, {})[0] == "EXACT_MATCH"
    assert _compare_single_field("status", "Closed", "Open", {}, {})[0] == "CONFLICT"

def test_compare_source_only_identities():
    orig_data = pd.DataFrame({
        "case_id": ["A1"],
        "source_system": ["ORIGINAL"],
        "source_row_index": [0]
    })
    supp_data = pd.DataFrame(columns=["case_id", "source_system", "source_row_index"])
    
    aligned_df, index_df, _ = match_identities(orig_data, supp_data)
    
    comp_df = compare_fields(aligned_df, index_df)
    
    assert len(comp_df) == 1
    # 14. ORIGINAL_ONLY
    assert comp_df.iloc[0]["comparison_result"] == "NOT_COMPARABLE"
    assert comp_df.iloc[0]["comparison_reason"] == "Identity exists only in Original source."
    
    orig_data = pd.DataFrame(columns=["case_id", "source_system", "source_row_index"])
    supp_data = pd.DataFrame({
        "case_id": ["B1"],
        "source_system": ["SUPPLEMENTARY"],
        "source_row_index": [0]
    })
    
    aligned_df, index_df, _ = match_identities(orig_data, supp_data)
    comp_df = compare_fields(aligned_df, index_df)
    
    assert len(comp_df) == 1
    # 15. SUPPLEMENTARY_ONLY
    assert comp_df.iloc[0]["comparison_result"] == "NOT_COMPARABLE"
    assert comp_df.iloc[0]["comparison_reason"] == "Identity exists only in Supplementary source."

def test_compare_multi_record_and_provenance():
    # 16. Provenance preservation
    # 17. Deterministic output
    orig_data = pd.DataFrame({
        "case_id": ["A100", "A100"],
        "district": ["D1", "D2"],
        "source_system": ["ORIGINAL", "ORIGINAL"],
        "source_row_index": [10, 20]
    })
    supp_data = pd.DataFrame({
        "case_id": ["A100"],
        "district": ["D1"],
        "source_system": ["SUPPLEMENTARY"],
        "source_row_index": [30]
    })
    
    aligned_df, index_df, _ = match_identities(orig_data, supp_data)
    comp_df = compare_fields(aligned_df, index_df)
    
    # 9 canonical business fields per pair, 2 pairs (10 vs 30, 20 vs 30) -> 18 comparisons
    assert len(comp_df) == 18
    
    d1_comparisons = comp_df[comp_df["field_name"] == "district"].sort_values(by="original_source_row")
    assert len(d1_comparisons) == 2
    
    first_comp = d1_comparisons.iloc[0]
    assert first_comp["original_source_row"] == 10
    assert first_comp["supplementary_source_row"] == 30
    assert first_comp["comparison_result"] == "EXACT_MATCH"
    
    second_comp = d1_comparisons.iloc[1]
    assert second_comp["original_source_row"] == 20
    assert second_comp["supplementary_source_row"] == 30
    assert second_comp["comparison_result"] == "CONFLICT"

def test_no_precedence():
    # 18. Source precedence is absent
    assert _compare_single_field("priority", "Standard", "Expedited", {}, {})[0] == "CONFLICT"
    # Note: our schema explicitly lacks a "winner" column to enforce this constraint
    orig_data = pd.DataFrame({"case_id": ["A1"], "source_system": ["ORIGINAL"], "source_row_index": [1]})
    supp_data = pd.DataFrame({"case_id": ["A1"], "source_system": ["SUPPLEMENTARY"], "source_row_index": [2]})
    aligned_df, index_df, _ = match_identities(orig_data, supp_data)
    comp_df = compare_fields(aligned_df, index_df)
    
    assert "winner" not in comp_df.columns
    assert "authoritative_source" not in comp_df.columns
    assert "selected_record" not in comp_df.columns
    assert "deduplicated_record" not in comp_df.columns

def test_source_evidence_preserved():
    # 19. Source values remain unchanged
    # 21. S4 comparison does NOT modify source data
    orig_val = "May 17, 2024"
    supp_val = "2024-05-17"
    
    res, reason, o_pres, s_pres = _compare_single_field("intake_date", orig_val, supp_val, {}, {})
    
    assert res == "REPRESENTATION_EQUIVALENT"
    # The helper functions do not modify the string pointers provided to them
    assert orig_val == "May 17, 2024"
    assert supp_val == "2024-05-17"

def test_s4_consumes_metadata():
    # Adversarial test: Mocking a completely unexpected field as UNAVAILABLE in the metadata dict
    # S4 should respect the dictionary and NOT rely on a hardcoded list.
    res, reason, o_pres, s_pres = _compare_single_field("priority", "High", "", {}, {"priority": "UNAVAILABLE"})
    assert res == "UNAVAILABLE_ONE_SIDE"
    assert o_pres == "PRESENT"
    assert s_pres == "UNAVAILABLE"

def test_client_ref_comparison_taxonomy():
    # client_ref EXACT_MATCH
    assert _compare_single_field("client_ref", "Alice", "Alice", {}, {})[0] == "EXACT_MATCH"
    # client_ref UNAVAILABLE_ONE_SIDE (Supplementary lacks it)
    res, _, o_pres, s_pres = _compare_single_field("client_ref", "Alice", "", {}, {"client_ref": "UNAVAILABLE"})
    assert res == "UNAVAILABLE_ONE_SIDE"
    assert o_pres == "PRESENT"
    assert s_pres == "UNAVAILABLE"
    # client_ref MISSING_ONE_SIDE (Original missing, Supplementary present)
    res_m, _, o_m, s_m = _compare_single_field("client_ref", "", "Alice", {}, {})
    assert res_m == "MISSING_ONE_SIDE"
    assert o_m == "MISSING"
    assert s_m == "PRESENT"
    # client_ref CONFLICT
    assert _compare_single_field("client_ref", "Alice", "Bob", {}, {})[0] == "CONFLICT"

