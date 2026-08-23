import hashlib
import json
from pathlib import Path

import pandas as pd

from dirty_data.s6_execution import execute
from dirty_data.s6_independent_verifier import independently_calculate


def test_same_day_is_zero():
    assert (pd.Timestamp("2024-01-01") - pd.Timestamp("2024-01-01")).days == 0


def test_s3_cardinality_controls_many_to_one():
    result = execute()
    obs = result["observations"]
    assert (obs[obs["population"] == "MANY_TO_ONE_PHYSICAL"]["cardinality"] == "MANY_TO_ONE").all()
    assert len(obs[obs["population"] == "MANY_TO_ONE_PHYSICAL"]) == 92


def test_original_only_duplicates_are_not_many_to_one():
    obs = execute()["observations"]
    duplicated = obs[obs["population"] == "ORIGINAL_ONLY_AMBIGUOUS"]
    assert len(duplicated) == 276
    assert not (duplicated["cardinality"] == "MANY_TO_ONE").any()


def test_primary_kpi_is_30_day_rate_and_median():
    q1 = execute()["q1"]
    assert set(q1["metric"]) == {"30_DAY_CLOSURE_RATE", "MEDIAN_CLOSURE_DURATION"}
    assert "average_days" not in q1.columns


def test_supplementary_only_is_separate():
    result = execute()
    assert len(result["observations"][result["observations"].population == "SUPPLEMENTARY_ONLY"]) == 780
    assert set(result["supplementary_only"]["population"]) == {"SUPPLEMENTARY_ONLY"}


def test_invalid_comparison_is_explicitly_excluded():
    result = execute()
    exclusions = result["exclusions"]
    assert len(exclusions) == 762
    assert set(exclusions["comparison_result"]) == {"INVALID_COMPARISON"}
    assert exclusions["rule_policy_id"].notna().all()


def test_q3_uses_2024_and_2025():
    assert set(execute()["q3"]["segment"]) == {"2024", "2025"}


def test_independent_verifier_agrees():
    result = execute()
    independent = independently_calculate()
    q1 = result["q1"]
    rate = q1[(q1.metric == "30_DAY_CLOSURE_RATE") & (q1.segment == "ALL")].iloc[0]
    median = q1[(q1.metric == "MEDIAN_CLOSURE_DURATION") & (q1.segment == "ALL")].iloc[0]
    assert int(rate.numerator) == independent["q1"]["numerator"]
    assert int(rate.denominator) == independent["q1"]["denominator"]
    assert float(median.value) == independent["q1"]["median"]
