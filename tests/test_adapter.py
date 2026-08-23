import pandas as pd
from dirty_data.adapter import adapt_original_to_canonical

def test_original_adapter_mappings():
    # 1. Provide a realistic record-level example using original structure
    raw_data = {
        "case_id": ["C123"],
        "client_ref": ["Smith"],
        "district": ["Weybridge"],
        "intake_date": ["2024-01-01"],
        "closure_date": ["2024-02-01"],
        "status": ["Closed"],
        "category": ["Standard"],
        "priority": ["High"],
        "caseworker_id": ["W99"],
        "contact_count": ["5"]
    }
    raw_df = pd.DataFrame(raw_data)
    
    canonical_df = adapt_original_to_canonical(raw_df)
    
    # 1. All original fields map to correct canonical fields
    assert canonical_df.loc[0, "case_id"] == "C123"
    assert canonical_df.loc[0, "district"] == "Weybridge"
    assert canonical_df.loc[0, "intake_date"] == "2024-01-01"
    assert canonical_df.loc[0, "closure_date"] == "2024-02-01"
    assert canonical_df.loc[0, "category"] == "Standard"
    assert canonical_df.loc[0, "priority"] == "High"
    assert canonical_df.loc[0, "caseworker_id"] == "W99"
    assert canonical_df.loc[0, "contact_count"] == "5"
    
    # 12. Source is identified as ORIGINAL
    assert canonical_df.loc[0, "source_system"] == "ORIGINAL"
    
    # 13. No original extract date fabricated
    assert canonical_df.loc[0, "extract_date"] == ""
    
    # 14. Status handling follows canonical semantics
    assert canonical_df.loc[0, "status"] == "Closed"
    
    # 16. Source-row traceability is preserved
    assert canonical_df.loc[0, "source_row_index"] == 0

def test_original_adapter_preserves_missing_values():
    raw_data = {
        "case_id": ["C124"],
        "client_ref": [""],
        "district": ["Weybridge"],
        "intake_date": ["2024-01-01"],
        "closure_date": [""],
        "status": ["Open"],
        "category": ["Standard"],
        "priority": [""],  # 10. Missing priority
        "caseworker_id": ["W99"],
        "contact_count": [""] # 11. Missing contact_count
    }
    raw_df = pd.DataFrame(raw_data)
    
    canonical_df = adapt_original_to_canonical(raw_df)
    
    # Ensure missingness remains missing and is not coerced to 0 or None inadvertently
    assert canonical_df.loc[0, "priority"] == ""
    assert canonical_df.loc[0, "contact_count"] == ""
    assert canonical_df.loc[0, "client_ref"] == ""
    assert canonical_df.loc[0, "closure_date"] == ""

def test_original_adapter_preserves_malformed_dates():
    # 15. Malformed date values are not silently converted into valid dates
    raw_data = {
        "case_id": ["C125"],
        "client_ref": ["Jones"],
        "district": ["Weybridge"],
        "intake_date": ["13/14/2024"], # Invalid
        "closure_date": ["not-a-date"], # Invalid
        "status": ["Closed"],
        "category": ["Standard"],
        "priority": ["High"],
        "caseworker_id": ["W99"],
        "contact_count": ["1"]
    }
    raw_df = pd.DataFrame(raw_data)
    
    canonical_df = adapt_original_to_canonical(raw_df)
    
    assert canonical_df.loc[0, "intake_date"] == "13/14/2024"
    assert canonical_df.loc[0, "closure_date"] == "not-a-date"
    
    # Status is preserved exactly from source, even if closure_date is malformed
    assert canonical_df.loc[0, "status"] == "Closed"

def test_original_adapter_is_deterministic():
    raw_data = {
        "case_id": ["C126", "C127"],
        "client_ref": ["", "A"],
        "district": ["Weybridge", "Northgate"],
        "intake_date": ["2024-01-01", "2024-02-01"],
        "closure_date": ["", ""],
        "status": ["Open", "Open"],
        "category": ["Standard", "Complex"],
        "priority": ["", ""],
        "caseworker_id": ["W99", "W100"],
        "contact_count": ["", "2"]
    }
    raw_df1 = pd.DataFrame(raw_data)
    raw_df2 = pd.DataFrame(raw_data)
    
    canonical_df1 = adapt_original_to_canonical(raw_df1)
    canonical_df2 = adapt_original_to_canonical(raw_df2)
    
    pd.testing.assert_frame_equal(canonical_df1, canonical_df2)
