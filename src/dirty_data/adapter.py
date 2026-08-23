import pandas as pd
from .schema import get_expected_columns

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
