import pandas as pd
import pytest
from dirty_data.analysis_spec import is_eligible_for_duration, classify_30_day_outcome, OBSERVATION_CUTOFF
from dirty_data.analyze import analyze_question_1, analyze_question_2, analyze_question_3

def test_classify_30_day_outcome():
    # 1. Closed in 10 days -> CLOSED_WITHIN_30
    assert classify_30_day_outcome(pd.Series({"intake_date": "2023-01-01", "closure_date": "2023-01-11", "status": "Closed"})) == "CLOSED_WITHIN_30_DAYS"
    
    # 2. Closed in exactly 30 days -> CLOSED_WITHIN_30
    assert classify_30_day_outcome(pd.Series({"intake_date": "2023-01-01", "closure_date": "2023-01-31", "status": "Closed"})) == "CLOSED_WITHIN_30_DAYS"
    
    # 3. Closed in 31 days -> NOT_CLOSED_BY_30
    assert classify_30_day_outcome(pd.Series({"intake_date": "2023-01-01", "closure_date": "2023-02-01", "status": "Closed"})) == "NOT_CLOSED_BY_30_DAYS"
    
    # 4. Open >30 days -> NOT_CLOSED_BY_30
    assert classify_30_day_outcome(pd.Series({"intake_date": "2025-11-01", "closure_date": "", "status": "Open"})) == "NOT_CLOSED_BY_30_DAYS"
    
    # 5. Open <30 days -> NOT_OBSERVABLE
    assert classify_30_day_outcome(pd.Series({"intake_date": "2025-12-15", "closure_date": "", "status": "Open"})) == "OUTCOME_NOT_OBSERVABLE"
    
    # 8. Invalid date -> excluded/NOT_OBSERVABLE
    assert classify_30_day_outcome(pd.Series({"intake_date": "invalid", "closure_date": "", "status": "Open"})) == "NOT_OBSERVABLE"
    
    # 10. Temporal contradiction -> NOT_OBSERVABLE
    assert classify_30_day_outcome(pd.Series({"intake_date": "2023-02-01", "closure_date": "2023-01-01", "status": "Closed"})) == "NOT_OBSERVABLE"

def test_is_eligible_for_duration():
    assert is_eligible_for_duration(
        pd.Series({"intake_date": "2023-01-01", "closure_date": "2023-02-01"}),
        pd.Series({"eligible_for_duration_analysis": True})
    ) == True
    
    # Missing closure date is FINE for eligibility (they just become NOT_CLOSED or NOT_OBSERVABLE later)
    assert is_eligible_for_duration(
        pd.Series({"intake_date": "2023-01-01", "closure_date": ""}),
        pd.Series({"eligible_for_duration_analysis": True})
    ) == True
    
    # Not eligible from Phase 3
    assert is_eligible_for_duration(
        pd.Series({"intake_date": "2023-01-01", "closure_date": "2023-02-01"}),
        pd.Series({"eligible_for_duration_analysis": False})
    ) == False
    
    # Temporal contradiction not caught by Phase 2/3
    assert is_eligible_for_duration(
        pd.Series({"intake_date": "2023-05-01", "closure_date": "2023-04-01"}),
        pd.Series({"eligible_for_duration_analysis": True})
    ) == False

def test_analyze_question_1():
    df = pd.DataFrame([
        {"source_row": 1, "intake_date": "2023-01-01", "closure_date": "2023-01-15", "status": "Closed"}, # 14 days -> CLOSED_WITHIN_30
        {"source_row": 2, "intake_date": "2023-02-01", "closure_date": "2023-04-01", "status": "Closed"}, # 59 days -> NOT_CLOSED_BY_30
        {"source_row": 3, "intake_date": "2025-12-20", "closure_date": "", "status": "Open"}  # <30 days obs -> NOT_OBSERVABLE
    ])
    rq = pd.DataFrame([
        {"source_row": 1, "eligible_for_duration_analysis": True},
        {"source_row": 2, "eligible_for_duration_analysis": True},
        {"source_row": 3, "eligible_for_duration_analysis": True}
    ])
    
    res = analyze_question_1(df, rq)
    
    # 2023: 1 <= 30 days, 1 > 30 days. Total 2. Denominator 2.
    assert res["results_by_year"]["2023"]["denominator"] == 2
    assert res["results_by_year"]["2023"]["numerator"] == 1
    assert res["results_by_year"]["2023"]["rate"] == 0.5
    
    # 2025: 1 NOT_OBSERVABLE. Denominator 0.
    assert res["results_by_year"]["2025"]["denominator"] == 0
    assert res["results_by_year"]["2025"]["not_observable_population"] == 1
    assert res["results_by_year"]["2025"]["coverage"] == 0.0

def test_analyze_question_3_missing_priority():
    df = pd.DataFrame([
        {"source_row": 1, "intake_date": "2023-01-01", "priority": float("nan")},
        {"source_row": 2, "intake_date": "2023-02-01", "priority": float("nan")},
        {"source_row": 3, "intake_date": "2024-01-01", "priority": "High"}
    ])
    rq = pd.DataFrame([
        {"source_row": 1},
        {"source_row": 2},
        {"source_row": 3}
    ])
    
    res = analyze_question_3(df, rq)
    assert res["confidence"] == "NOT ANSWERABLE"
    assert res["evidence"]["2023_total_cases"] == 2
    assert res["evidence"]["2023_missing_priority"] == 2
    assert res["evidence"]["defensible_proxy_exists"] == False
