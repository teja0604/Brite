import pandas as pd
from typing import Tuple, Dict, List
import re
from datetime import datetime

from .contract import analyze_date_format

def parse_date_safely(date_str: str) -> pd.Timestamp:
    if not isinstance(date_str, str) or date_str == "":
        return pd.NaT
        
    format_class = analyze_date_format(date_str)
    
    if format_class == "CANONICAL":
        return pd.to_datetime(date_str, format="%Y-%m-%d")
        
    if format_class == "DATE_FORMAT_VARIATION":
        # Usually things like "May 17, 2024" or unambiguously ordered numeric dates.
        # We can lean on pandas for unambiguous ones, but must catch exceptions
        try:
            return pd.to_datetime(date_str, dayfirst=False) # default behaviour
        except Exception:
            return pd.NaT
            
    # AMBIGUOUS_DATE_FORMAT and INVALID_DATE return NaT
    return pd.NaT

def evaluate_kpis(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Evaluates business KPIs strictly on the available dataset (reconciled or baseline).
    Produces Physical KPIs, Case-Level KPIs, Exclusions, and Many-to-One anomalies.
    """
    base = df.copy()
    
    # Ensure parsed dates
    if "parsed_intake" not in base.columns:
        base["parsed_intake"] = base["intake_date"].apply(lambda d: parse_date_safely(d))
    if "parsed_closure" not in base.columns:
        base["parsed_closure"] = base["closure_date"].apply(lambda d: parse_date_safely(d))
        
    base["is_closed"] = base["status"].astype(str).str.strip().str.lower() == "closed"
    base["valid_dates"] = base["parsed_intake"].notna() & base["parsed_closure"].notna()
    
    # Same-day = 0 days
    base["duration_days"] = (base["parsed_closure"] - base["parsed_intake"]).dt.days
    
    # Negative durations are invalid dates
    base.loc[base["duration_days"] < 0, "valid_dates"] = False
    
    # Identify supplementary only
    if "original_source_row" in base.columns:
        base["is_supp_only"] = base["original_source_row"].isna() | (base["original_source_row"] == "")
    else:
        base["is_supp_only"] = False
        
    # Isolate MANY_TO_ONE identities
    # A case_id is MANY_TO_ONE if it appears > 1 time in the dataset.
    counts = base["case_id"].value_counts()
    many_to_one_ids = set(counts[counts > 1].index)
    
    base["is_many_to_one"] = base["case_id"].isin(many_to_one_ids)
    
    # Create the anomaly dataframe for MANY_TO_ONE
    many_to_one_anomaly_df = base[base["is_many_to_one"]].copy()
    
    kpis_phys = []
    kpis_case = []
    exclusions = []
    
    base["intake_year"] = base["parsed_intake"].dt.year
    
    segments = [
        ("Year", "intake_year"),
        ("District", "district"),
        ("Category", "category")
    ]
    
    for seg_name, col_name in segments:
        base[f"{col_name}_str"] = base[col_name].astype(str).str.strip()
        
        if "field_availability" in base.columns:
            base[f"{col_name}_unavail"] = base["field_availability"].apply(lambda a: isinstance(a, dict) and a.get(col_name) == "UNAVAILABLE")
        else:
            base[f"{col_name}_unavail"] = False
            
        base[f"{col_name}_miss"] = (base[f"{col_name}_str"] == "") & ~base[f"{col_name}_unavail"]
        
        unavail_df = base[base[f"{col_name}_unavail"]]
        miss_df = base[base[f"{col_name}_miss"]]
        
        for cid in unavail_df["case_id"]:
            exclusions.append({"case_id": cid, "context": f"{seg_name} Segment", "reason": "Unavailable segment value"})
        for cid in miss_df["case_id"]:
            exclusions.append({"case_id": cid, "context": f"{seg_name} Segment", "reason": "Missing segment value"})
            
        valid_seg = base[base["is_closed"] & base["valid_dates"] & ~base[f"{col_name}_unavail"] & ~base[f"{col_name}_miss"]]
        
        # PHYSICAL GROUPING (All valid records)
        grouped_phys = valid_seg.groupby([f"{col_name}_str", "is_supp_only"])["duration_days"].agg(["sum", "count"]).reset_index()
        for _, row in grouped_phys.iterrows():
            num = row["sum"]
            den = row["count"]
            q_label = "Q1_Trend" if seg_name == "Year" else f"Q2_{seg_name}"
            kpis_phys.append({
                "question": q_label,
                "segment": f"{seg_name}: {row[f'{col_name}_str']}",
                "supp_only": row["is_supp_only"],
                "numerator_total_days": num,
                "denominator": den,
                "average_days": num / den if den > 0 else 0
            })
            
        # CASE GROUPING (OPTION C: Only ONE_TO_ONE records)
        valid_case_seg = valid_seg[~valid_seg["is_many_to_one"]]
        grouped_case = valid_case_seg.groupby([f"{col_name}_str", "is_supp_only"])["duration_days"].agg(["sum", "count"]).reset_index()
        for _, row in grouped_case.iterrows():
            num = row["sum"]
            den = row["count"]
            q_label = "Q1_Trend" if seg_name == "Year" else f"Q2_{seg_name}"
            kpis_case.append({
                "question": q_label,
                "segment": f"{seg_name}: {row[f'{col_name}_str']}",
                "supp_only": row["is_supp_only"],
                "numerator_total_days": num,
                "denominator": den,
                "average_days": num / den if den > 0 else 0
            })

    # Overall Q1
    valid_q1 = base[base["is_closed"] & base["valid_dates"]]
    open_cases = base[~base["is_closed"]]
    invalid_dates = base[base["is_closed"] & ~base["valid_dates"]]
    for cid in open_cases["case_id"]:
        exclusions.append({"case_id": cid, "context": "Q1_Overall", "reason": "Open case"})
    for cid in invalid_dates["case_id"]:
        exclusions.append({"case_id": cid, "context": "Q1_Overall", "reason": "Invalid or missing dates"})
        
    for is_supp in [True, False]:
        v_phys = valid_q1[valid_q1["is_supp_only"] == is_supp]
        kpis_phys.append({
            "question": "Q1_Overall", "segment": "All", "supp_only": is_supp,
            "numerator_total_days": v_phys["duration_days"].sum() if not v_phys.empty else 0,
            "denominator": len(v_phys),
            "average_days": v_phys["duration_days"].mean() if not v_phys.empty else 0
        })
        
        v_case = v_phys[~v_phys["is_many_to_one"]]
        kpis_case.append({
            "question": "Q1_Overall", "segment": "All", "supp_only": is_supp,
            "numerator_total_days": v_case["duration_days"].sum() if not v_case.empty else 0,
            "denominator": len(v_case),
            "average_days": v_case["duration_days"].mean() if not v_case.empty else 0
        })
        
    # Q3 High Priority
    def is_priority_unavail(avail):
        return isinstance(avail, dict) and avail.get("priority") == "UNAVAILABLE"

    base["priority_str"] = base["priority"].astype(str).str.strip()
    if "field_availability" in base.columns:
        base["priority_unavail"] = base["field_availability"].apply(is_priority_unavail)
    else:
        base["priority_unavail"] = False
        
    base["priority_miss"] = (base["priority_str"] == "") & ~base["priority_unavail"]
    base["is_high"] = base["priority_str"].str.lower() == "high"
    
    unavail_df = base[base["priority_unavail"]]
    miss_df = base[base["priority_miss"]]
    for cid in unavail_df["case_id"]:
        exclusions.append({"case_id": cid, "context": "Priority Segment", "reason": "Unavailable segment value"})
    for cid in miss_df["case_id"]:
        exclusions.append({"case_id": cid, "context": "Priority Segment", "reason": "Missing segment value"})
        
    high_valid = base[base["is_high"] & base["is_closed"] & base["valid_dates"]]
    q3_valid = high_valid[high_valid["intake_year"].isin([2024, 2025])]
    
    high_base = base[base["is_high"]]
    open_high = high_base[~high_base["is_closed"]]
    invalid_high = high_base[high_base["is_closed"] & ~high_base["valid_dates"]]
    for cid in open_high["case_id"]:
        exclusions.append({"case_id": cid, "context": "Q3_HighPriority", "reason": "Open case"})
    for cid in invalid_high["case_id"]:
        exclusions.append({"case_id": cid, "context": "Q3_HighPriority", "reason": "Invalid or missing dates"})

    grouped_phys_q3 = q3_valid.groupby(["intake_year", "is_supp_only"])["duration_days"].agg(["sum", "count"]).reset_index()
    for _, row in grouped_phys_q3.iterrows():
        num = row["sum"]
        den = row["count"]
        kpis_phys.append({
            "question": "Q3_HighPriority_2024_vs_2025",
            "segment": f"High Priority: {int(row['intake_year'])}",
            "supp_only": row["is_supp_only"],
            "numerator_total_days": num,
            "denominator": den,
            "average_days": num / den if den > 0 else 0
        })
        
    q3_valid_case = q3_valid[~q3_valid["is_many_to_one"]]
    grouped_case_q3 = q3_valid_case.groupby(["intake_year", "is_supp_only"])["duration_days"].agg(["sum", "count"]).reset_index()
    for _, row in grouped_case_q3.iterrows():
        num = row["sum"]
        den = row["count"]
        kpis_case.append({
            "question": "Q3_HighPriority_2024_vs_2025",
            "segment": f"High Priority: {int(row['intake_year'])}",
            "supp_only": row["is_supp_only"],
            "numerator_total_days": num,
            "denominator": den,
            "average_days": num / den if den > 0 else 0
        })

    return pd.DataFrame(kpis_phys), pd.DataFrame(kpis_case), pd.DataFrame(exclusions), many_to_one_anomaly_df
