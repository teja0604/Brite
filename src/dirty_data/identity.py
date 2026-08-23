import pandas as pd
from typing import Tuple, Dict, Any

def match_identities(orig_canonical: pd.DataFrame, supp_canonical: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Deterministically aligns Original and Supplementary records by identity (case_id).
    Calculates overlap metrics dynamically.
    Does NOT deduplicate, merge values, or discard conflicting records.
    """
    # 1. Calculate dynamic overlap metrics
    # Drop empty strings to avoid treating them as a valid case_id
    orig_ids = set(orig_canonical[orig_canonical['case_id'] != '']['case_id'].unique())
    supp_ids = set(supp_canonical[supp_canonical['case_id'] != '']['case_id'].unique())
    
    overlap = orig_ids.intersection(supp_ids)
    
    metrics = {
        "original_unique": len(orig_ids),
        "supplementary_unique": len(supp_ids),
        "overlap": len(overlap),
        "original_only": len(orig_ids - supp_ids),
        "supplementary_only": len(supp_ids - orig_ids)
    }
    
    # 2. Align records without dropping or merging values
    # Concatenating preserves all records and their provenance metadata (source_system, source_row_index).
    # Sorting groups them strictly by identity, creating a multi-source ledger per case_id.
    aligned_df = pd.concat([orig_canonical, supp_canonical], ignore_index=True)
    
    # We sort by case_id, source_system, and source_row_index to ensure deterministic ordering.
    aligned_df = aligned_df.sort_values(by=["case_id", "source_system", "source_row_index"]).reset_index(drop=True)
    
    return aligned_df, metrics
