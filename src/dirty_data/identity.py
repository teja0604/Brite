import pandas as pd
from typing import Tuple, Dict, Any

def _compute_match_status(orig_count: int, supp_count: int) -> str:
    if orig_count > 0 and supp_count > 0:
        return "MATCHED"
    if orig_count > 0 and supp_count == 0:
        return "ORIGINAL_ONLY"
    return "SUPPLEMENTARY_ONLY"

def _compute_cardinality(orig_count: int, supp_count: int) -> str:
    if orig_count == 1 and supp_count == 1:
        return "ONE_TO_ONE"
    if orig_count > 1 and supp_count == 1:
        return "MANY_TO_ONE"
    if orig_count == 1 and supp_count > 1:
        return "ONE_TO_MANY"
    if orig_count > 1 and supp_count > 1:
        return "MANY_TO_MANY"
    if orig_count > 0 and supp_count == 0:
        return "ORIGINAL_ONLY"
    return "SUPPLEMENTARY_ONLY"

def match_identities(orig_canonical: pd.DataFrame, supp_canonical: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Deterministically aligns Original and Supplementary records by identity (case_id).
    Returns:
      1. aligned_df: A flattened ledger containing every physical canonical row, safely sorted.
      2. identity_index_df: An explicit identity-level artifact declaring match relationships and cardinality.
      3. metrics: Overlap statistics.
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
    
    # 3. Build Identity Index
    # Explicitly calculate physical row counts to support cardinality
    orig_counts = orig_canonical[orig_canonical['case_id'] != '']['case_id'].value_counts()
    supp_counts = supp_canonical[supp_canonical['case_id'] != '']['case_id'].value_counts()
    
    all_case_ids = sorted(list(orig_ids.union(supp_ids)))
    
    index_records = []
    for cid in all_case_ids:
        orig_c = int(orig_counts.get(cid, 0))
        supp_c = int(supp_counts.get(cid, 0))
        index_records.append({
            "case_id": cid,
            "original_count": orig_c,
            "supplementary_count": supp_c,
            "match_status": _compute_match_status(orig_c, supp_c),
            "cardinality": _compute_cardinality(orig_c, supp_c)
        })
        
    identity_index_df = pd.DataFrame(index_records)
    
    return aligned_df, identity_index_df, metrics
