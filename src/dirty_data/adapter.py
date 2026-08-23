import pandas as pd
from .schema import get_expected_columns
from .contract import analyze_date_format

def adapt_original_to_canonical(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Translates the validated Original source dataframe into the Canonical model.
    This does NOT perform data cleaning, anomaly detection, or reconciliation.
    """
    # Create a clean copy to avoid modifying the raw source DataFrame
    canonical_df = raw_df.copy()
    
    # 1. Direct Mappings
    # The original source fields (case_id, client_ref, district, intake_date, 
    # closure_date, status, category, priority, caseworker_id, contact_count)
    # perfectly align with the CANONICAL_SCHEMA names. 
    # No column renaming is necessary for the Original source.
    
    # 2. Status Handling
    # The canonical model treats 'status' as derived from 'closure_date'.
    # However, the Original source explicitly provides 'status'.
    # We preserve the provided 'status' verbatim rather than re-deriving it,
    # ensuring we don't accidentally validate or fix malformed dates at the adapter layer.
    
    # 3. Missing Value Preservation
    # Missing fields (e.g. contact_count = "") are preserved as empty strings,
    # distinguishing them from fabricated 0s.
    
    # 4. Source Traceability
    # Preserve the original row index to trace canonical records back to the raw CSV row.
    canonical_df['source_row_index'] = canonical_df.index
    
    # 5. Source Metadata
    # Mark the record's origin for future field-level reconciliation.
    canonical_df['source_system'] = 'ORIGINAL'
    
    # 6. Extract Date
    # The Original source does not contain an extract_date.
    # Preserve missingness as an empty string (or None) rather than fabricating a date.
    canonical_df['extract_date'] = ''
    
    # Ensure only canonical columns plus traceability metadata are returned
    expected_canonical = get_expected_columns('canonical')
    final_columns = expected_canonical + ['source_row_index']
    
    # Reorder and filter columns
    canonical_df = canonical_df[final_columns]
    
    return canonical_df

def derive_supplementary_status(closed_val: str) -> str:
    """
    Derives canonical status conceptually from the supplementary closure_date.
    - EMPTY closure date -> Open
    - VALID closure date -> Closed
    - INVALID / malformed / ambiguous closure value -> do not manufacture certainty ("")
    """
    closed_val = str(closed_val).strip()
    if closed_val == "":
        return "Open"
        
    format_class = analyze_date_format(closed_val)
    if format_class in ["CANONICAL", "DATE_FORMAT_VARIATION"]:
        return "Closed"
        
    return ""

def adapt_supplementary_to_canonical(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Translates the validated Supplementary source dataframe into the Canonical model.
    """
    canonical_df = pd.DataFrame()
    
    # 1. Direct Mappings
    canonical_df['case_id'] = raw_df['reference']
    canonical_df['district'] = raw_df['office']
    canonical_df['intake_date'] = raw_df['opened']
    canonical_df['closure_date'] = raw_df['closed']
    canonical_df['category'] = raw_df['case_type']
    canonical_df['priority'] = raw_df['band']
    canonical_df['caseworker_id'] = raw_df['worker']
    
    # 2. Extract Date
    # Explicitly present in the supplementary source
    canonical_df['extract_date'] = raw_df['extract_date']
    
    # 3. Unavailable Fields
    # The supplementary source does not contain client_ref or contact_count.
    # We must explicitly mark them as missing/unavailable (""), NOT fabricating 0 or default values.
    canonical_df['client_ref'] = ''
    canonical_df['contact_count'] = ''
    
    # 4. Status Handling
    # The supplementary source lacks a status column. We conceptually derive it 
    # without silently converting malformed source evidence into a valid business state.
    canonical_df['status'] = raw_df['closed'].apply(derive_supplementary_status)
    
    # 5. Source Metadata
    canonical_df['source_system'] = 'SUPPLEMENTARY'
    
    # 6. Source Traceability
    # Preserve the original row index
    canonical_df['source_row_index'] = raw_df.index
    
    # Ensure only canonical columns plus traceability metadata are returned
    expected_canonical = get_expected_columns('canonical')
    final_columns = expected_canonical + ['source_row_index']
    
    # Reorder and filter columns
    canonical_df = canonical_df[final_columns]
    
    return canonical_df
