import pandas as pd
from dirty_data.identity import match_identities
from dirty_data.adapter import adapt_original_to_canonical, adapt_supplementary_to_canonical

def test_match_identities_cardinalities_and_index():
    # 1-6. Comprehensive Cardinality coverage
    # A1: ONE_TO_ONE
    # A2: ORIGINAL_ONLY
    # A3: SUPPLEMENTARY_ONLY
    # A4: MANY_TO_ONE (2 orig, 1 supp)
    # A5: ONE_TO_MANY (1 orig, 2 supp)
    # A6: MANY_TO_MANY (2 orig, 2 supp)
    
    orig_data = {
        "case_id": ["A1", "A2", "A4", "A4", "A5", "A6", "A6"],
        "source_system": ["ORIGINAL"] * 7,
        "source_row_index": [0, 1, 2, 3, 4, 5, 6]
    }
    orig_df = pd.DataFrame(orig_data)
    
    supp_data = {
        "case_id": ["A1", "A3", "A4", "A5", "A5", "A6", "A6"],
        "source_system": ["SUPPLEMENTARY"] * 7,
        "source_row_index": [0, 1, 2, 3, 4, 5, 6]
    }
    supp_df = pd.DataFrame(supp_data)
    
    aligned_df, index_df, metrics = match_identities(orig_df, supp_df)
    
    # 7. Physical duplicate rows are preserved (7 + 7 = 14)
    assert len(aligned_df) == 14
    
    # 8. Identity index has exactly one row per unique case_id
    assert len(index_df) == 6
    assert index_df['case_id'].nunique() == 6
    
    # Check A1: ONE_TO_ONE
    a1 = index_df[index_df["case_id"] == "A1"].iloc[0]
    assert a1["match_status"] == "MATCHED"
    assert a1["cardinality"] == "ONE_TO_ONE"
    assert a1["original_count"] == 1
    assert a1["supplementary_count"] == 1
    
    # Check A2: ORIGINAL_ONLY
    a2 = index_df[index_df["case_id"] == "A2"].iloc[0]
    assert a2["match_status"] == "ORIGINAL_ONLY"
    assert a2["cardinality"] == "ORIGINAL_ONLY"
    assert a2["original_count"] == 1
    assert a2["supplementary_count"] == 0
    
    # Check A3: SUPPLEMENTARY_ONLY
    a3 = index_df[index_df["case_id"] == "A3"].iloc[0]
    assert a3["match_status"] == "SUPPLEMENTARY_ONLY"
    assert a3["cardinality"] == "SUPPLEMENTARY_ONLY"
    assert a3["original_count"] == 0
    assert a3["supplementary_count"] == 1
    
    # Check A4: MANY_TO_ONE
    a4 = index_df[index_df["case_id"] == "A4"].iloc[0]
    assert a4["match_status"] == "MATCHED"
    assert a4["cardinality"] == "MANY_TO_ONE"
    assert a4["original_count"] == 2
    assert a4["supplementary_count"] == 1
    
    # Check A5: ONE_TO_MANY
    a5 = index_df[index_df["case_id"] == "A5"].iloc[0]
    assert a5["match_status"] == "MATCHED"
    assert a5["cardinality"] == "ONE_TO_MANY"
    assert a5["original_count"] == 1
    assert a5["supplementary_count"] == 2
    
    # Check A6: MANY_TO_MANY
    a6 = index_df[index_df["case_id"] == "A6"].iloc[0]
    assert a6["match_status"] == "MATCHED"
    assert a6["cardinality"] == "MANY_TO_MANY"
    assert a6["original_count"] == 2
    assert a6["supplementary_count"] == 2
    
    # 9. Identity index counts match actual physical rows
    assert index_df["original_count"].sum() == len(orig_df)
    assert index_df["supplementary_count"].sum() == len(supp_df)
    
    # 12. Deterministic output (sorting is applied correctly in index_df)
    assert index_df["case_id"].tolist() == ["A1", "A2", "A3", "A4", "A5", "A6"]

def test_match_identities_real_data():
    orig_raw = pd.read_csv('data/raw/case-export-2023-2025.csv', dtype=str, keep_default_na=False)
    orig_can = adapt_original_to_canonical(orig_raw)
    
    supp_raw = pd.read_csv('data/raw/2 - Dirty Data, Real Decisions/case-export-supplementary.csv', dtype=str, keep_default_na=False)
    supp_can = adapt_supplementary_to_canonical(supp_raw)
    
    aligned_df, index_df, metrics = match_identities(orig_can, supp_can)
    
    # 10. Real-data row conservation remains: 15,100 + 4,180 = 19,280
    assert len(aligned_df) == 19280
    
    # 11. Real-data overlap remains dynamically calculated
    assert metrics["original_unique"] == 14916
    assert metrics["supplementary_unique"] == 4180
    assert metrics["overlap"] == 3400
    assert metrics["original_only"] == 11516
    assert metrics["supplementary_only"] == 780
    
    # Identity index checks for real data
    assert len(index_df) == 14916 + 780
    
    # Ensure physical counts correctly map
    assert index_df["original_count"].sum() == 15100
    assert index_df["supplementary_count"].sum() == 4180

def test_match_identities_duplicate_identity_analysis():
    # Specific test proving duplicate identities produce correct cardinality without removal
    orig_data = {
        "case_id": ["A100", "A100"],
        "source_system": ["ORIGINAL", "ORIGINAL"],
        "source_row_index": [0, 1]
    }
    orig_df = pd.DataFrame(orig_data)
    
    supp_data = {
        "case_id": ["A100"],
        "source_system": ["SUPPLEMENTARY"],
        "source_row_index": [0]
    }
    supp_df = pd.DataFrame(supp_data)
    
    aligned_df, index_df, metrics = match_identities(orig_df, supp_df)
    
    assert len(aligned_df) == 3
    
    a100 = index_df.iloc[0]
    assert a100["case_id"] == "A100"
    assert a100["original_count"] == 2
    assert a100["supplementary_count"] == 1
    assert a100["match_status"] == "MATCHED"
    assert a100["cardinality"] == "MANY_TO_ONE"
