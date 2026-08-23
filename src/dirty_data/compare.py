import pandas as pd
from typing import List, Dict, Any, Tuple
from .contract import analyze_date_format

COMPARISON_FIELDS = [
    "client_ref",
    "district",
    "intake_date",
    "closure_date",
    "status",
    "category",
    "priority",
    "caseworker_id",
    "contact_count"
]

# Hardcoded domain facts are NO LONGER ALLOWED in S4.
# We strictly consume canonical field_availability.

def _parse_unambiguous_date(val: str) -> str:
    # A simplified date parser for known formats (since analyze_date_format returns format class, not parsed date)
    # The detect/remediate logic uses pandas to parse unambiguous dates.
    try:
        dt = pd.to_datetime(val, format="mixed", dayfirst=False)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""

def _compare_single_field(field_name: str, orig_val: str, supp_val: str, orig_avail: dict, supp_avail: dict) -> Tuple[str, str, str, str]:
    """
    Returns (result, reason, orig_presence, supp_presence)
    """
    orig_has = orig_avail.get(field_name) != "UNAVAILABLE"
    supp_has = supp_avail.get(field_name) != "UNAVAILABLE"
    
    orig_presence = "PRESENT" if orig_has else "UNAVAILABLE"
    supp_presence = "PRESENT" if supp_has else "UNAVAILABLE"
    
    # If the field exists in the schema but is empty, it's MISSING
    if orig_has and orig_val == "":
        orig_presence = "MISSING"
    if supp_has and supp_val == "":
        supp_presence = "MISSING"
        
    if orig_presence == "UNAVAILABLE" or supp_presence == "UNAVAILABLE":
        return "UNAVAILABLE_ONE_SIDE", f"{field_name} is unavailable in one schema", orig_presence, supp_presence
        
    if orig_presence == "MISSING" and supp_presence == "PRESENT":
        return "MISSING_ONE_SIDE", "Original value is missing", orig_presence, supp_presence
        
    if supp_presence == "MISSING" and orig_presence == "PRESENT":
        return "MISSING_ONE_SIDE", "Supplementary value is missing", orig_presence, supp_presence
        
    if orig_presence == "MISSING" and supp_presence == "MISSING":
        return "EXACT_MATCH", "Both missing", orig_presence, supp_presence
        
    if orig_val == supp_val:
        return "EXACT_MATCH", "Values match exactly", orig_presence, supp_presence
        
    # Date specific handling
    if field_name in ["intake_date", "closure_date"]:
        orig_fmt = analyze_date_format(orig_val)
        supp_fmt = analyze_date_format(supp_val)
        
        if orig_fmt in ["INVALID_DATE", "AMBIGUOUS_DATE_FORMAT"] or supp_fmt in ["INVALID_DATE", "AMBIGUOUS_DATE_FORMAT"]:
            return "INVALID_COMPARISON", "One or both dates are malformed/ambiguous", orig_presence, supp_presence
            
        # If both are valid (CANONICAL or DATE_FORMAT_VARIATION)
        orig_parsed = _parse_unambiguous_date(orig_val)
        supp_parsed = _parse_unambiguous_date(supp_val)
        
        if orig_parsed == supp_parsed and orig_parsed != "":
            return "REPRESENTATION_EQUIVALENT", "Different formats but equivalent dates", orig_presence, supp_presence
            
        return "CONFLICT", "Dates represent different days", orig_presence, supp_presence
        
    return "CONFLICT", "Values are different", orig_presence, supp_presence

def compare_fields(aligned_df: pd.DataFrame, identity_index_df: pd.DataFrame) -> pd.DataFrame:
    """
    Performs field-level comparisons across all canonical records.
    Implements Cartesian product matching for multi-record cases.
    """
    records = []
    
    # Pre-group aligned_df by case_id to speed up lookups
    grouped = aligned_df.groupby("case_id")
    
    for idx_row in identity_index_df.itertuples():
        case_id = idx_row.case_id
        match_status = idx_row.match_status
        cardinality = idx_row.cardinality
        
        if match_status == "ORIGINAL_ONLY":
            records.append({
                "case_id": case_id,
                "cardinality": cardinality,
                "field_name": "ALL",
                "original_value": "",
                "supplementary_value": "",
                "original_presence": "UNAVAILABLE",
                "supplementary_presence": "UNAVAILABLE",
                "original_source_row": -1,
                "supplementary_source_row": -1,
                "comparison_result": "NOT_COMPARABLE",
                "comparison_reason": "Identity exists only in Original source."
            })
            continue
            
        if match_status == "SUPPLEMENTARY_ONLY":
            records.append({
                "case_id": case_id,
                "cardinality": cardinality,
                "field_name": "ALL",
                "original_value": "",
                "supplementary_value": "",
                "original_presence": "UNAVAILABLE",
                "supplementary_presence": "UNAVAILABLE",
                "original_source_row": -1,
                "supplementary_source_row": -1,
                "comparison_result": "NOT_COMPARABLE",
                "comparison_reason": "Identity exists only in Supplementary source."
            })
            continue
            
        # Match case
        case_data = grouped.get_group(case_id)
        orig_data = case_data[case_data['source_system'] == 'ORIGINAL']
        supp_data = case_data[case_data['source_system'] == 'SUPPLEMENTARY']
        
        # Cartesian product of physical rows
        for o_row in orig_data.itertuples():
            for s_row in supp_data.itertuples():
                
                for field in COMPARISON_FIELDS:
                    o_val = str(getattr(o_row, field, ""))
                    s_val = str(getattr(s_row, field, ""))
                    
                    o_avail = getattr(o_row, "field_availability", {})
                    s_avail = getattr(s_row, "field_availability", {})
                    
                    result, reason, o_pres, s_pres = _compare_single_field(field, o_val, s_val, o_avail, s_avail)
                    
                    records.append({
                        "case_id": case_id,
                        "cardinality": cardinality,
                        "field_name": field,
                        "original_value": o_val,
                        "supplementary_value": s_val,
                        "original_presence": o_pres,
                        "supplementary_presence": s_pres,
                        "original_source_row": o_row.source_row_index,
                        "supplementary_source_row": s_row.source_row_index,
                        "comparison_result": result,
                        "comparison_reason": reason
                    })
                    
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values(by=["case_id", "field_name", "original_source_row", "supplementary_source_row"]).reset_index(drop=True)
    return df
