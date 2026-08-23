import pandas as pd
from dirty_data.adapter import adapt_original_to_canonical, adapt_supplementary_to_canonical, derive_supplementary_status

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

def test_supplementary_adapter_mappings():
    raw_data = {
        "reference": ["S999"],
        "office": ["Calder Central"],
        "opened": ["2024-03-01"],
        "closed": ["2024-04-01"],
        "case_type": ["Complex"],
        "band": ["Low"],
        "worker": ["W10"],
        "extract_date": ["2026-01-14"]
    }
    raw_df = pd.DataFrame(raw_data)
    
    canonical_df = adapt_supplementary_to_canonical(raw_df)
    
    # 1-8. Direct mappings
    assert canonical_df.loc[0, "case_id"] == "S999"
    assert canonical_df.loc[0, "district"] == "Calder Central"
    assert canonical_df.loc[0, "intake_date"] == "2024-03-01"
    assert canonical_df.loc[0, "closure_date"] == "2024-04-01"
    assert canonical_df.loc[0, "category"] == "Complex"
    assert canonical_df.loc[0, "priority"] == "Low"
    assert canonical_df.loc[0, "caseworker_id"] == "W10"
    assert canonical_df.loc[0, "extract_date"] == "2026-01-14"
    
    # 9. source_system = SUPPLEMENTARY
    assert canonical_df.loc[0, "source_system"] == "SUPPLEMENTARY"
    
    # 12-13. client_ref and contact_count are not fabricated
    assert canonical_df.loc[0, "client_ref"] == ""
    assert canonical_df.loc[0, "contact_count"] == ""
    
    # 14. Status is derived based on closure_date (VALID date present -> Closed)
    assert canonical_df.loc[0, "status"] == "Closed"
    
    # 16. source row traceability
    assert canonical_df.loc[0, "source_row_index"] == 0

def test_supplementary_adapter_missing_values():
    raw_data = {
        "reference": ["S1000"],
        "office": ["Calder Central"],
        "opened": ["2024-03-01"],
        "closed": [""],
        "case_type": ["Complex"],
        "band": [""], # missing band
        "worker": ["W10"],
        "extract_date": ["2026-01-14"]
    }
    raw_df = pd.DataFrame(raw_data)
    canonical_df = adapt_supplementary_to_canonical(raw_df)
    
    # 10. missing band remains missing
    assert canonical_df.loc[0, "priority"] == ""
    
    # 11. missing closed remains missing
    assert canonical_df.loc[0, "closure_date"] == ""
    
    # 14. EMPTY closure date -> Open
    assert canonical_df.loc[0, "status"] == "Open"

def test_supplementary_adapter_malformed_dates():
    # 15. malformed closure values are not silently converted into valid dates/status
    raw_data = {
        "reference": ["S1001"],
        "office": ["Calder Central"],
        "opened": ["2024-03-01"],
        "closed": ["not-a-date"],
        "case_type": ["Complex"],
        "band": ["Low"],
        "worker": ["W10"],
        "extract_date": ["2026-01-14"]
    }
    raw_df = pd.DataFrame(raw_data)
    canonical_df = adapt_supplementary_to_canonical(raw_df)
    
    # The malformed date is preserved
    assert canonical_df.loc[0, "closure_date"] == "not-a-date"
    
    # Status is empty because date is malformed (do not manufacture certainty)
    assert canonical_df.loc[0, "status"] == ""

def test_derive_supplementary_status():
    # EMPTY -> Open
    assert derive_supplementary_status("") == "Open"
    assert derive_supplementary_status("   ") == "Open"
    
    # VALID -> Closed
    assert derive_supplementary_status("2024-01-01") == "Closed"
    assert derive_supplementary_status("January 1, 2024") == "Closed"
    
    # INVALID / AMBIGUOUS -> ""
    assert derive_supplementary_status("not-a-date") == ""
    assert derive_supplementary_status("03-04-2024") == "" # ambiguous format

def test_supplementary_real_data():
    # 19. actual 4,180-row supplementary input can pass through the adapter
    raw_df = pd.read_csv('data/raw/2 - Dirty Data, Real Decisions/case-export-supplementary.csv', dtype=str, keep_default_na=False)
    canonical_df = adapt_supplementary_to_canonical(raw_df)
    
    assert len(canonical_df) == 4180
    assert canonical_df['case_id'].nunique() == 4180
    assert (canonical_df['source_system'] == 'SUPPLEMENTARY').all()
