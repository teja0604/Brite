import pandas as pd
from dirty_data.identity import match_identities
from dirty_data.adapter import adapt_original_to_canonical, adapt_supplementary_to_canonical

def test_match_identities_synthetic():
    orig_data = {
        "case_id": ["C1", "C2", "C3", "C3"], # C3 is an exact duplicate in original
        "district": ["D1", "D2", "D3", "D3"],
        "status": ["Open", "Closed", "Open", "Open"],
        "source_system": ["ORIGINAL", "ORIGINAL", "ORIGINAL", "ORIGINAL"],
        "source_row_index": [0, 1, 2, 3]
    }
    orig_df = pd.DataFrame(orig_data)
    
    supp_data = {
        "case_id": ["C2", "C3", "C4"],
        "district": ["D2_supp", "D3_supp", "D4_supp"],
        "status": ["Closed", "Closed", "Open"], # Conflict on C3 status
        "source_system": ["SUPPLEMENTARY", "SUPPLEMENTARY", "SUPPLEMENTARY"],
        "source_row_index": [0, 1, 2]
    }
    supp_df = pd.DataFrame(supp_data)
    
    aligned_df, metrics = match_identities(orig_df, supp_df)
    
    # 1. Total rows = 4 + 3 = 7
    assert len(aligned_df) == 7
    
    # 2. Check dynamic metrics
    assert metrics["original_unique"] == 3  # C1, C2, C3
    assert metrics["supplementary_unique"] == 3  # C2, C3, C4
    assert metrics["overlap"] == 2  # C2, C3
    assert metrics["original_only"] == 1  # C1
    assert metrics["supplementary_only"] == 1  # C4
    
    # 3. Check determinism / structure
    # Since it's sorted by case_id -> source_system -> source_row_index
    # C1: orig
    # C2: orig, supp
    # C3: orig, orig, supp
    # C4: supp
    expected_ids = ["C1", "C2", "C2", "C3", "C3", "C3", "C4"]
    assert aligned_df["case_id"].tolist() == expected_ids
    
    expected_sources = [
        "ORIGINAL", 
        "ORIGINAL", "SUPPLEMENTARY", 
        "ORIGINAL", "ORIGINAL", "SUPPLEMENTARY", 
        "SUPPLEMENTARY"
    ]
    assert aligned_df["source_system"].tolist() == expected_sources
    
    # 4. Check that values were not overwritten or dropped
    c3_supp = aligned_df[(aligned_df["case_id"] == "C3") & (aligned_df["source_system"] == "SUPPLEMENTARY")].iloc[0]
    assert c3_supp["district"] == "D3_supp"
    assert c3_supp["status"] == "Closed"
    
    c3_orig_1 = aligned_df[(aligned_df["case_id"] == "C3") & (aligned_df["source_system"] == "ORIGINAL")].iloc[0]
    assert c3_orig_1["district"] == "D3"
    assert c3_orig_1["status"] == "Open"

def test_match_identities_real_data():
    orig_raw = pd.read_csv('data/raw/case-export-2023-2025.csv', dtype=str, keep_default_na=False)
    orig_can = adapt_original_to_canonical(orig_raw)
    
    supp_raw = pd.read_csv('data/raw/2 - Dirty Data, Real Decisions/case-export-supplementary.csv', dtype=str, keep_default_na=False)
    supp_can = adapt_supplementary_to_canonical(supp_raw)
    
    aligned_df, metrics = match_identities(orig_can, supp_can)
    
    # 1. Total rows = 15,100 + 4,180 = 19,280
    assert len(aligned_df) == 19280
    
    # 2. Check empirically established overlap metrics
    assert metrics["original_unique"] == 14916
    assert metrics["supplementary_unique"] == 4180
    assert metrics["overlap"] == 3400
    assert metrics["original_only"] == 11516
    assert metrics["supplementary_only"] == 780
    
    # 3. Verify deterministic sorting ensures grouped output
    # First record should be the lowest case_id alphanumerically
    # By grouping we ensure we don't have overlapping indices
    case_groups = aligned_df.groupby("case_id").size()
    assert len(case_groups) == 14916 + 780
