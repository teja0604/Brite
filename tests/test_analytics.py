import pandas as pd
import pytest
from dirty_data.analytics import evaluate_kpis

def create_mock_row(**kwargs):
    default = {
        "case_id": "1",
        "intake_date": "2023-01-01",
        "closure_date": "2023-01-10",
        "status": "Closed",
        "priority": "High",
        "district": "Northgate",
        "category": "Standard",
        "caseworker_id": "CW1",
        "client_ref": "REF1"
    }
    default.update(kwargs)
    return default

def test_date_subtraction_same_day():
    df = pd.DataFrame([create_mock_row(closure_date="2023-01-01")])
    kpi_phys, kpi_case, excl, anom = evaluate_kpis(df)
    q1 = kpi_phys[(kpi_phys["question"] == "Q1_Overall") & (~kpi_phys["supp_only"])]
    assert q1["average_days"].iloc[0] == 0

def test_date_subtraction_cross_year():
    df = pd.DataFrame([create_mock_row(intake_date="2023-12-31", closure_date="2024-01-01")])
    kpi_phys, kpi_case, excl, anom = evaluate_kpis(df)
    q1 = kpi_phys[(kpi_phys["question"] == "Q1_Overall") & (~kpi_phys["supp_only"])]
    assert q1["average_days"].iloc[0] == 1

def test_denominator_conservation():
    df = pd.DataFrame([
        create_mock_row(case_id="1", intake_date="2024-01-01", closure_date="2024-01-10"), # Valid, year=2024, duration=9, High priority
        create_mock_row(case_id="2", closure_date="", status="Open"), # Open
        create_mock_row(case_id="3", intake_date="2023-13-01"), # Invalid date
        create_mock_row(case_id="4", priority=""), # Missing priority
        create_mock_row(case_id="5", priority="", field_availability={"priority": "UNAVAILABLE"}), # Unavailable priority
        create_mock_row(case_id="6", intake_date="2024-01-10", closure_date="2024-01-01"), # Negative duration (Invalid date)
    ])
    kpi_results_phys, kpi_results_case, exclusions, anomaly_df = evaluate_kpis(df)
    
    q1 = kpi_results_phys[(kpi_results_phys["question"] == "Q1_Overall") & (~kpi_results_phys["supp_only"])]
    # Valid records: case 1, 4, 5. Invalid/open: 2, 3, 6.
    assert q1["denominator"].iloc[0] == 3
    
    q3 = kpi_results_phys[(kpi_results_phys["question"] == "Q3_HighPriority_2024_vs_2025") & (~kpi_results_phys["supp_only"])]
    # Only case_id="1" is valid for Q3.
    assert q3["denominator"].iloc[0] == 1
    
    # Exclusions
    q1_excl = exclusions[exclusions["context"] == "Q1_Overall"]
    assert len(q1_excl[q1_excl["reason"] == "Open case"]) == 1
    # Invalid or missing dates should include case_id 3 and 6
    invalid_date_excls = q1_excl[q1_excl["reason"] == "Invalid or missing dates"]
    assert len(invalid_date_excls) == 2
    assert set(invalid_date_excls["case_id"]) == {"3", "6"}
    
    seg_excl = exclusions[exclusions["context"] == "Priority Segment"]
    assert len(seg_excl[seg_excl["reason"] == "Missing segment value"]) == 1
    assert len(seg_excl[seg_excl["reason"] == "Unavailable segment value"]) == 1

def test_many_to_one_aggregation():
    df = pd.DataFrame([
        create_mock_row(case_id="ID1", intake_date="2023-01-01", closure_date="2023-01-11"), # 10 days
        create_mock_row(case_id="ID1", intake_date="2023-01-02", closure_date="2023-01-14"), # 12 days
        create_mock_row(case_id="ID2", intake_date="2023-01-01", closure_date="2023-01-05")  # 4 days
    ])
    kpi_results_phys, kpi_results_case, _, anomaly = evaluate_kpis(df)
    
    q1_phys = kpi_results_phys[(kpi_results_phys["question"] == "Q1_Overall") & (~kpi_results_phys["supp_only"])]
    assert q1_phys["denominator"].iloc[0] == 3
    assert q1_phys["numerator_total_days"].iloc[0] == 26 # 10 + 12 + 4
    
    q1_case = kpi_results_case[(kpi_results_case["question"] == "Q1_Overall") & (~kpi_results_case["supp_only"])]
    # Under Option C, ID1 is MANY_TO_ONE and must be entirely excluded from case-level KPIs
    assert q1_case["denominator"].iloc[0] == 1 # Only ID2
    assert q1_case["numerator_total_days"].iloc[0] == 4 # Only ID2's duration
    
    # Verify the anomaly DataFrame catches ID1's two physical rows
    assert len(anomaly) == 2
    assert set(anomaly["case_id"]) == {"ID1"}
