import pandas as pd
from typing import Tuple, List, Dict, Any
from .schema import get_expected_columns

def reconcile_dataset(
    aligned_df: pd.DataFrame, 
    identity_index_df: pd.DataFrame, 
    comparison_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Applies the Phase S5 reconciliation policy to the S4 comparison evidence.
    Returns (reconciled_df, reconciliation_audit_df).
    
    This first pass handles:
    - EXACT_MATCH
    - REPRESENTATION_EQUIVALENT (Retains Original formatting)
    - UNAVAILABLE_ONE_SIDE (Retains available evidence)
    - MISSING_ONE_SIDE (Imputes present evidence)
    - NOT_COMPARABLE (Source-only records pass through using Original if available)
    
    Conflicts and Multi-Record identities will be addressed in the second commit.
    """
    reconciled_records = []
    audit_logs = []
    unresolved_records = []
    
    # We only process ONE_TO_ONE and ORIGINAL_ONLY cases for this commit logic.
    # We will exclude MULTI_RECORD and SUPPLEMENTARY_ONLY for now (or pass them through as unresolved later).
    
    canonical_cols = get_expected_columns('canonical')
    
    # Pre-group aligned_df for quick lookups of client_ref and extract_date 
    # (fields that S4 doesn't explicitly compare but we must carry over).
    aligned_grouped = aligned_df.groupby("case_id")
    comp_grouped = comparison_df.groupby("case_id")
    
    for idx_row in identity_index_df.itertuples():
        case_id = idx_row.case_id
        cardinality = idx_row.cardinality
        match_status = idx_row.match_status
        
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        if cardinality in ["ONE_TO_MANY", "MANY_TO_MANY"]:
            case_data = aligned_grouped.get_group(case_id)
            for _, row in case_data.iterrows():
                unresolved_records.append({
                    "case_id": case_id,
                    "source_system": row["source_system"],
                    "source_row_index": row["source_row_index"],
                    "reason": f"Identity requires explicit multi-record handling ({cardinality}).",
                    "rule_applied": "RULE-S5-COMPLEX-MULTI"
                })
            audit_logs.append({
                "case_id": case_id,
                "field": "ALL",
                "original_source_row": "",
                "supplementary_source_row": "",
                "original_value": "MULTIPLE",
                "supplementary_value": "MULTIPLE",
                "comparison_result": "NOT_COMPARABLE",
                "reconciliation_decision": "UNRESOLVED_MULTI_RECORD",
                "selected_value": "",
                "reason": f"Identity requires explicit multi-record handling ({cardinality}).",
                "rule_applied": "RULE-S5-COMPLEX-MULTI"
            })
            continue

        if match_status == "ORIGINAL_ONLY":
            # Pass through the original record exactly as-is
            case_data = aligned_grouped.get_group(case_id)
            orig_rows = case_data[case_data["source_system"] == "ORIGINAL"]
            for _, orig_row_s in orig_rows.iterrows():
                orig_row = orig_row_s.to_dict()
                orig_idx = orig_row.get("source_row_index", "")
                
                reconciled_rec = {col: orig_row.get(col, "") for col in canonical_cols}
                reconciled_rec["reconciliation_status"] = "ORIGINAL_ONLY"
                reconciled_records.append(reconciled_rec)
                
                audit_logs.append({
                    "case_id": case_id,
                    "field": "ALL",
                    "original_source_row": orig_idx,
                    "supplementary_source_row": "",
                    "original_value": "PRESENT",
                    "supplementary_value": "UNAVAILABLE",
                    "comparison_result": "NOT_COMPARABLE",
                    "reconciliation_decision": "PASS_THROUGH",
                    "selected_value": "ORIGINAL",
                    "reason": "Identity exists only in Original source",
                    "rule_applied": "RULE-S5-ORIGINAL-ONLY"
                })
            continue
            
        if match_status == "SUPPLEMENTARY_ONLY":
            # Pass through the supplementary record exactly as-is
            case_data = aligned_grouped.get_group(case_id)
            supp_rows = case_data[case_data["source_system"] == "SUPPLEMENTARY"]
            for _, supp_row_s in supp_rows.iterrows():
                supp_row = supp_row_s.to_dict()
                supp_idx = supp_row.get("source_row_index", "")
                
                reconciled_rec = {col: supp_row.get(col, "") for col in canonical_cols}
                reconciled_rec["reconciliation_status"] = "SUPPLEMENTARY_ONLY"
                reconciled_records.append(reconciled_rec)
                
                audit_logs.append({
                    "case_id": case_id,
                    "field": "ALL",
                    "original_source_row": "",
                    "supplementary_source_row": supp_idx,
                    "original_value": "UNAVAILABLE",
                    "supplementary_value": "PRESENT",
                    "comparison_result": "NOT_COMPARABLE",
                    "reconciliation_decision": "PASS_THROUGH",
                    "selected_value": "SUPPLEMENTARY",
                    "reason": "Identity exists only in Supplementary source",
                    "rule_applied": "RULE-S5-SUPPLEMENTARY-ONLY"
                })
            continue
            
        # MATCHED logic (handles ONE_TO_ONE and MANY_TO_ONE via grouping)
        comp_rows = comp_grouped.get_group(case_id)
        
        # We group by original_source_row to produce exactly one reconciled record per Original physical row
        # This elegantly handles MANY_TO_ONE without deduplicating or dropping the 46 cases.
        for orig_idx, pair_group in comp_rows.groupby("original_source_row"):
            case_data = aligned_grouped.get_group(case_id)
            orig_row = case_data[(case_data["source_system"] == "ORIGINAL") & (case_data["source_row_index"] == orig_idx)].iloc[0]
            
            reconciled_rec = {"case_id": case_id}
            
            # Carry over non-compared fields safely
            reconciled_rec["client_ref"] = orig_row.get("client_ref", "")
            reconciled_rec["extract_date"] = orig_row.get("extract_date", "")
            reconciled_rec["source_system"] = "RECONCILED"
            
            has_conflict = False
            supp_idx = pair_group["supplementary_source_row"].iloc[0]
            
            # Explicitly log extract_date provenance
            orig_ext = str(orig_row.get("extract_date", ""))
            case_supp_rows = case_data[case_data["source_system"] == "SUPPLEMENTARY"]
            supp_ext = str(case_supp_rows.iloc[0].get("extract_date", "")) if not case_supp_rows.empty else ""
            
            audit_logs.append({
                "case_id": case_id,
                "field": "extract_date",
                "original_source_row": orig_idx,
                "supplementary_source_row": supp_idx,
                "original_value": orig_ext,
                "supplementary_value": supp_ext,
                "comparison_result": "PROVENANCE_ONLY",
                "reconciliation_decision": "RETAIN_PROVENANCE",
                "selected_value": orig_ext,
                "reason": "Retain source provenance for extraction date without treating as conflict.",
                "rule_applied": "RULE-S5-EXTRACT-DATE"
            })
        
            for c_row in pair_group.itertuples():
                field = c_row.field_name
                res = c_row.comparison_result
                o_val = str(c_row.original_value)
                s_val = str(c_row.supplementary_value)
                
                selected_val = ""
                decision = ""
                rule = ""
                reason = ""
                
                if res == "EXACT_MATCH":
                    selected_val = o_val
                    decision = "RETAIN_MATCH"
                    rule = "RULE-S5-MATCH"
                    reason = "Values match exactly"
                    
                elif res == "REPRESENTATION_EQUIVALENT":
                    # Option 1: Retain Original string representation
                    selected_val = o_val
                    decision = "RETAIN_ORIGINAL_FORMAT"
                    rule = "RULE-S5-REP-EQUIV"
                    reason = "Values are equivalent; defaulting to original baseline formatting"
                    
                elif res == "UNAVAILABLE_ONE_SIDE":
                    # Retain the side that has the field
                    if c_row.original_presence == "PRESENT" or c_row.original_presence == "MISSING":
                        selected_val = o_val
                        decision = "RETAIN_ORIGINAL_AVAILABLE"
                        rule = "RULE-S5-UNAVAILABLE"
                        reason = "Field unavailable in Supplementary; preserving Original evidence"
                    else:
                        selected_val = s_val
                        decision = "RETAIN_SUPPLEMENTARY_AVAILABLE"
                        rule = "RULE-S5-UNAVAILABLE"
                        reason = "Field unavailable in Original; preserving Supplementary evidence"
                        
                elif res == "MISSING_ONE_SIDE":
                    # Option 1: Impute from the present side
                    if c_row.original_presence == "MISSING":
                        selected_val = s_val
                        decision = "IMPUTE_FROM_SUPPLEMENTARY"
                        rule = "RULE-S5-IMPUTE"
                        reason = "Original is missing; imputing from present Supplementary value"
                    else:
                        selected_val = o_val
                        decision = "IMPUTE_FROM_ORIGINAL"
                        rule = "RULE-S5-IMPUTE"
                        reason = "Supplementary is missing; imputing from present Original value"
                        
                elif res in ["CONFLICT", "INVALID_COMPARISON"]:
                    # Option 3 (Field-specific): Supplementary wins for status and closure_date
                    has_conflict = True
                    if field in ["status", "closure_date"]:
                        selected_val = s_val
                        decision = "SUPPLEMENTARY_WINS"
                        rule = "RULE-S5-CONFLICT"
                        reason = "Supplementary source provides authoritative operational updates for this field."
                    else:
                        selected_val = o_val
                        decision = "ORIGINAL_WINS"
                        rule = "RULE-S5-CONFLICT"
                        reason = "Original source retains precedence for this field to prevent arbitrary baseline churn."
                
                reconciled_rec[field] = selected_val
                
                audit_logs.append({
                    "case_id": case_id,
                    "field": field,
                    "original_source_row": orig_idx,
                    "supplementary_source_row": supp_idx,
                    "original_value": o_val,
                    "supplementary_value": s_val,
                    "comparison_result": res,
                    "reconciliation_decision": decision,
                    "selected_value": selected_val,
                    "reason": reason,
                    "rule_applied": rule
                })
                
            reconciled_rec["reconciliation_status"] = "CONFLICT" if has_conflict else "CLEAN"
            reconciled_records.append(reconciled_rec)
        
    recon_df = pd.DataFrame(reconciled_records)
    
    # Ensure columns match schema
    if not recon_df.empty:
        cols = [c for c in canonical_cols if c in recon_df.columns] + ["reconciliation_status"]
        recon_df = recon_df[cols]
        
    audit_df = pd.DataFrame(audit_logs)
    unresolved_df = pd.DataFrame(unresolved_records)
    return recon_df, unresolved_df, audit_df
