import pandas as pd
from typing import Dict, Any

OBSERVATION_CUTOFF = pd.to_datetime("2025-12-31")

def classify_30_day_outcome(row: pd.Series) -> str:
    """
    Classifies a case's 30-day outcome to handle right-censoring correctly.
    Returns one of:
    - CLOSED_WITHIN_30_DAYS
    - NOT_CLOSED_BY_30_DAYS
    - OUTCOME_NOT_OBSERVABLE
    """
    intake = pd.to_datetime(row.get("intake_date", ""), errors="coerce")
    closure = pd.to_datetime(row.get("closure_date", ""), errors="coerce")
    status = row.get("status", "")
    
    if pd.isna(intake):
        return "NOT_OBSERVABLE"
        
    if not pd.isna(closure):
        # We have a closure date
        duration = (closure - intake).days
        if duration < 0:
            return "NOT_OBSERVABLE" # Temporal contradiction
        if duration <= 30:
            return "CLOSED_WITHIN_30_DAYS"
        else:
            return "NOT_CLOSED_BY_30_DAYS"
            
    # Case is open (closure date is missing)
    follow_up_days = (OBSERVATION_CUTOFF - intake).days
    if follow_up_days >= 30:
        return "NOT_CLOSED_BY_30_DAYS"
    else:
        return "OUTCOME_NOT_OBSERVABLE"

def is_eligible_for_duration(row: pd.Series, quality_row: pd.Series) -> bool:
    if not quality_row.get("eligible_for_duration_analysis", False):
        return False
        
    intake = pd.to_datetime(row.get("intake_date", ""), errors="coerce")
    closure = pd.to_datetime(row.get("closure_date", ""), errors="coerce")
    
    if pd.isna(intake):
        return False
        
    if not pd.isna(closure):
        if (closure - intake).days < 0:
            return False
            
    return True

QUESTIONS = {
    "Q1": {
        "id": "Q1",
        "original_question": "Have case closure times increased between 2023 and 2025, and if so, by how much?",
        "business_meaning": "Determine if there is a systemic increase in the time it takes to close cases.",
        "target_population": "All unique cases with valid intake dates.",
        "unit_of_analysis": "Unique Case (source record surviving deduplication)",
        "metric_formula": "30-day closure rate = CLOSED_WITHIN_30_DAYS / (CLOSED_WITHIN_30_DAYS + NOT_CLOSED_BY_30_DAYS)",
        "eligibility_func": is_eligible_for_duration,
        "numerator_func": lambda df: df[df["outcome_30d"] == "CLOSED_WITHIN_30_DAYS"],
        "denominator_func": lambda df: df[df["outcome_30d"].isin(["CLOSED_WITHIN_30_DAYS", "NOT_CLOSED_BY_30_DAYS"])],
        "treatment_of_missing": "Cases missing valid intake dates or those without 30 days of observation are excluded from the denominator.",
        "treatment_of_duplicates": "Exact duplicates dropped. Candidates retained.",
        "limitations": "Median duration is reported as a secondary metric but is right-censored for recent cohorts."
    },
    "Q2": {
        "id": "Q2",
        "original_question": "If closure times have changed, what is driving the change?",
        "business_meaning": "Identify operational segments (districts, categories) where closure performance deviates significantly from the baseline.",
        "target_population": "All unique cases with valid, interpretable intake and closure dates.",
        "unit_of_analysis": "Unique Case (source record surviving deduplication)",
        "metric_formula": "30-day closure rate segmented by district, category, and composition (district x category).",
        "eligibility_func": is_eligible_for_duration,
        "numerator_func": lambda df: df[df["outcome_30d"] == "CLOSED_WITHIN_30_DAYS"],
        "denominator_func": lambda df: df[df["outcome_30d"].isin(["CLOSED_WITHIN_30_DAYS", "NOT_CLOSED_BY_30_DAYS"])],
        "treatment_of_missing": "Same as Q1. Segments with high unresolved/uncontrolled category mappings are preserved without false consolidation.",
        "treatment_of_duplicates": "Same as Q1.",
        "limitations": "The dataset cannot prove causation (e.g., *why* a district's performance dropped). Semantic category variants are strictly not merged, which may disperse insights across artificial categories."
    },
    "Q3": {
        "id": "Q3",
        "original_question": "Did the case triage process introduced during 2024 reduce closure times for high-priority cases?",
        "business_meaning": "Evaluate the efficacy of the 2024 triage process on high-priority case resolution times.",
        "target_population": "High-priority cases pre- and post-triage rollout.",
        "unit_of_analysis": "Unique Case",
        "metric_formula": "N/A",
        "eligibility_func": None,
        "numerator_func": None,
        "denominator_func": None,
        "treatment_of_missing": "N/A",
        "treatment_of_duplicates": "N/A",
        "limitations": "The 'priority' field is completely empty (100% NaN) for all cases in 2023. We lack the pre-triage baseline necessary to determine if closure times for high-priority cases *reduced* relative to before the process was introduced."
    }
}
