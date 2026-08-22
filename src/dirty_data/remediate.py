import pandas as pd
from typing import Tuple, Dict, Any, List
import re
from datetime import datetime

class Disposition:
    AUTO_REPAIR = "AUTO_REPAIR"
    RETAIN_WITH_FLAG = "RETAIN_WITH_FLAG"
    EXCLUDE_FROM_ANALYSIS = "EXCLUDE_FROM_ANALYSIS"
    UNRESOLVED = "UNRESOLVED"

def parse_unambiguous_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
        
    match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", date_str)
    if match:
        p1, p2, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if p1 > 12:
            month, day = p2, p1
        else:
            month, day = p1, p2
        dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d")
    raise ValueError(f"Cannot parse {date_str} as unambiguous")

def normalize_category_formatting(cat_str: str) -> str:
    s = re.sub(r'\s+', ' ', cat_str)
    s = s.strip()
    # Be careful not to lowercase everything if we just want Title Case, but .title() does that.
    return s.title()

def remediate_dataset(raw_df: pd.DataFrame, anomalies_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit_log = []
    cleaned_rows = []
    quality_rows = []
    
    anomalies_by_row = {}
    for _, a in anomalies_df.iterrows():
        sr = a["source_row"]
        if sr not in anomalies_by_row:
            anomalies_by_row[sr] = []
        anomalies_by_row[sr].append(a.to_dict())
        
    data_cols = [c for c in raw_df.columns if c != "source_row"]
    raw_dicts = raw_df.to_dict(orient="records")
    for i, row in enumerate(raw_dicts):
        row["source_row"] = i + 1
        
    seen_exact = {}
    duplicate_source_rows = set()
    
    # ID Deduplication
    for row in raw_dicts:
        sr = row["source_row"]
        row_sig = tuple(str(row[c]) for c in data_cols)
        if row_sig in seen_exact:
            duplicate_source_rows.add(sr)
            audit_log.append({
                "source_row": sr,
                "field": "all",
                "original_value": str(row_sig),
                "cleaned_value": "",
                "rule_id": "RULE-ID-001",
                "action": "Drop exact duplicate",
                "disposition": Disposition.AUTO_REPAIR,
                "reason": f"Exact duplicate of source_row {seen_exact[row_sig]}"
            })
        else:
            seen_exact[row_sig] = sr

    for row in raw_dicts:
        sr = row["source_row"]
        if sr in duplicate_source_rows:
            continue
            
        cleaned_row = dict(row)
        q = {
            "source_row": sr,
            "case_id": row.get("case_id", ""),
            "record_status": "CLEAN",
            "eligible_for_duration_analysis": True,
            "eligible_for_case_counts": True,
            "eligible_for_category_analysis": True,
            "quality_flags": []
        }
        
        row_anomalies = anomalies_by_row.get(sr, [])
        row_audit_start_idx = len(audit_log)
        
        # Identity / Conflict check
        for a in row_anomalies:
            if a["anomaly_type"] == "CANDIDATE_IDENTITY_VARIANT":
                q["quality_flags"].append("CANDIDATE_IDENTITY_VARIANT")
                audit_log.append({
                    "source_row": sr,
                    "field": "case_id",
                    "original_value": row.get("case_id", ""),
                    "cleaned_value": row.get("case_id", ""),
                    "rule_id": "RULE-ID-003",
                    "action": "Retain without merging",
                    "disposition": Disposition.RETAIN_WITH_FLAG,
                    "reason": "Candidate identity variant identified, semantic proof insufficient to merge"
                })

        # Process Dates (intake_date, closure_date)
        for date_field in ["intake_date", "closure_date"]:
            val = row.get(date_field, "")
            field_anomalies = [a for a in row_anomalies if a["field"] == date_field]
            
            if val == "":
                # Missingness logic
                if date_field == "closure_date":
                    status = row.get("status", "")
                    if status != "Open":
                        q["eligible_for_duration_analysis"] = False
                        audit_log.append({
                            "source_row": sr, "field": "closure_date", "original_value": "", "cleaned_value": "",
                            "rule_id": "RULE-DATE-006", "action": "Retain unexpected missing",
                            "disposition": Disposition.UNRESOLVED, "reason": "closure_date empty for Closed/Unknown status"
                        })
                else:
                    audit_log.append({
                        "source_row": sr, "field": date_field, "original_value": "", "cleaned_value": "",
                        "rule_id": "RULE-DATE-008", "action": "Retain unexpected missing",
                        "disposition": Disposition.UNRESOLVED, "reason": f"{date_field} is missing"
                    })
            else:
                has_invalid = any(a["anomaly_type"] == "INVALID_DATE" for a in field_anomalies)
                has_ambig = any(a["anomaly_type"] == "AMBIGUOUS_DATE_FORMAT" for a in field_anomalies)
                has_var = any(a["anomaly_type"] == "DATE_FORMAT_VARIATION" for a in field_anomalies)
                
                if has_invalid:
                    q["eligible_for_duration_analysis"] = False
                    audit_log.append({
                        "source_row": sr, "field": date_field, "original_value": val, "cleaned_value": val,
                        "rule_id": "RULE-DATE-004", "action": "Flag invalid date",
                        "disposition": Disposition.UNRESOLVED, "reason": "Unparseable or impossible calendar date"
                    })
                elif has_ambig:
                    q["eligible_for_duration_analysis"] = False
                    audit_log.append({
                        "source_row": sr, "field": date_field, "original_value": val, "cleaned_value": val,
                        "rule_id": "RULE-DATE-003", "action": "Flag ambiguous date",
                        "disposition": Disposition.UNRESOLVED, "reason": "Date format is ambiguous (e.g. MM/DD vs DD/MM)"
                    })
                elif has_var:
                    try:
                        clean_val = parse_unambiguous_date(val)
                        cleaned_row[date_field] = clean_val
                        audit_log.append({
                            "source_row": sr, "field": date_field, "original_value": val, "cleaned_value": clean_val,
                            "rule_id": "RULE-DATE-002", "action": "Repair unambiguous format",
                            "disposition": Disposition.AUTO_REPAIR, "reason": "Date unambiguously parsed to canonical YYYY-MM-DD"
                        })
                    except Exception:
                        q["eligible_for_duration_analysis"] = False
                        audit_log.append({
                            "source_row": sr, "field": date_field, "original_value": val, "cleaned_value": val,
                            "rule_id": "RULE-DATE-004", "action": "Failed to parse variant",
                            "disposition": Disposition.UNRESOLVED, "reason": "Format marked variant but failed deterministic parsing"
                        })
                else:
                    # CANONICAL -> No audit entry needed
                    pass

        # Temporal Contradiction
        temp_anomalies = [a for a in row_anomalies if a["anomaly_type"] == "LOGICAL_CONTRADICTION" and a["field"] == "closure_date"]
        if temp_anomalies:
            q["eligible_for_duration_analysis"] = False
            audit_log.append({
                "source_row": sr, "field": "closure_date", "original_value": row.get("closure_date", ""), "cleaned_value": row.get("closure_date", ""),
                "rule_id": "RULE-DATE-007", "action": "Exclude from duration analysis",
                "disposition": Disposition.EXCLUDE_FROM_ANALYSIS, "reason": "Unambiguous closure_date is before intake_date"
            })
            
        # Category
        cat_val = row.get("category", "")
        cat_anomalies = [a for a in row_anomalies if a["field"] == "category"]
        if cat_val != "":
            is_variant = any(a["anomaly_type"] == "CANDIDATE_CATEGORY_VARIANT" for a in cat_anomalies)
            
            formatted_cat = normalize_category_formatting(cat_val)
            
            if cat_val != formatted_cat:
                cleaned_row["category"] = formatted_cat
                audit_log.append({
                    "source_row": sr, "field": "category", "original_value": cat_val, "cleaned_value": formatted_cat,
                    "rule_id": "RULE-CAT-001", "action": "Normalize formatting",
                    "disposition": Disposition.AUTO_REPAIR, "reason": "Formatting-only normalization (whitespace/casing)"
                })
                
            # Even if formatted, it might still be a semantic variant
            if is_variant and cat_val == formatted_cat:
                # If it's a semantic variant (e.g. Std. vs Standard) but formatting was clean
                q["quality_flags"].append("UNRESOLVED_SEMANTIC_CATEGORY")
                audit_log.append({
                    "source_row": sr, "field": "category", "original_value": cat_val, "cleaned_value": cleaned_row["category"],
                    "rule_id": "RULE-CAT-003", "action": "Retain semantic variant",
                    "disposition": Disposition.UNRESOLVED, "reason": "Candidate semantic variant without explicit mapping evidence"
                })
                    
        # Missing Priority
        if row.get("priority", "") == "":
            audit_log.append({
                "source_row": sr, "field": "priority", "original_value": "", "cleaned_value": "",
                "rule_id": "RULE-MISS-001", "action": "Retain missing priority",
                "disposition": Disposition.UNRESOLVED, "reason": "No evidence to safely impute priority"
            })
            
        # Numeric Contact Count
        cc = row.get("contact_count", "")
        if cc != "" and not cc.isdigit():
            q["eligible_for_case_counts"] = False
            audit_log.append({
                "source_row": sr, "field": "contact_count", "original_value": cc, "cleaned_value": cc,
                "rule_id": "RULE-NUM-001", "action": "Flag invalid contact_count",
                "disposition": Disposition.UNRESOLVED, "reason": "Value is not a valid positive integer"
            })
            
        q["quality_flags"] = "|".join(q["quality_flags"])
        
        # Calculate record-level disposition
        row_dispositions = [a["disposition"] for a in audit_log[row_audit_start_idx:]]
        if Disposition.EXCLUDE_FROM_ANALYSIS in row_dispositions:
            q["record_status"] = Disposition.EXCLUDE_FROM_ANALYSIS
        elif Disposition.UNRESOLVED in row_dispositions:
            q["record_status"] = Disposition.UNRESOLVED
        elif Disposition.RETAIN_WITH_FLAG in row_dispositions:
            q["record_status"] = Disposition.RETAIN_WITH_FLAG
        elif Disposition.AUTO_REPAIR in row_dispositions:
            q["record_status"] = Disposition.AUTO_REPAIR
        else:
            q["record_status"] = "CLEAN"
        
        cleaned_rows.append(cleaned_row)
        quality_rows.append(q)
        
    audit_df = pd.DataFrame(audit_log, columns=["source_row", "field", "original_value", "cleaned_value", "rule_id", "action", "disposition", "reason"]) if audit_log else pd.DataFrame(columns=["source_row", "field", "original_value", "cleaned_value", "rule_id", "action", "disposition", "reason"])
    return pd.DataFrame(cleaned_rows), audit_df, pd.DataFrame(quality_rows)
