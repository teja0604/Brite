from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .contract import analyze_date_format
from .s6_artifact_contract import validate_frozen_artifacts
from .s6_independent_verifier import independently_calculate
from .s6_population import build_population_disposition


def _production_metrics(output_dir):
    root = Path(output_dir)
    q1 = pd.read_csv(root / "q1.csv")
    q3 = pd.read_csv(root / "q3.csv")
    obs = pd.read_csv(root / "observations.csv")
    exclusions = pd.read_csv(root / "exclusions.csv")
    return q1, q3, obs, exclusions


def verify(production_dir="outputs/s6", frozen_dir="outputs/frozen"):
    manifest = validate_frozen_artifacts(frozen_dir)
    expected = independently_calculate(frozen_dir)
    q1, q3, obs, exclusions = _production_metrics(production_dir)
    rate = q1[(q1.metric == "30_DAY_CLOSURE_RATE") & (q1.segment == "ALL")].iloc[0]
    median = q1[(q1.metric == "MEDIAN_CLOSURE_DURATION") & (q1.segment == "ALL")].iloc[0]
    checks = {
        "q1_numerator": int(rate.numerator) == expected["q1"]["numerator"],
        "q1_denominator": int(rate.denominator) == expected["q1"]["denominator"],
        "q1_rate": abs(float(rate.value) - expected["q1"]["numerator"] / expected["q1"]["denominator"]) < 1e-12,
        "q1_median": float(median.value) == expected["q1"]["median"],
        "many_to_one_rows": int((obs.population == "MANY_TO_ONE_PHYSICAL").sum()) == expected["many_to_one_rows"],
        "supplementary_only_rows": int((obs.population == "SUPPLEMENTARY_ONLY").sum()) == expected["supplementary_only_rows"],
        "invalid_comparison_rows": len(exclusions) == 762 and set(exclusions["comparison_result"]) == {"INVALID_COMPARISON"},
    }
    for year in ("2024", "2025"):
        rows = q3[(q3.metric == "30_DAY_CLOSURE_RATE") & (q3.segment == year)]
        med_rows = q3[(q3.metric == "MEDIAN_CLOSURE_DURATION") & (q3.segment == year)]
        checks[f"q3_{year}_rate"] = not rows.empty and int(rows.iloc[0].numerator) == expected["q3"][year]["numerator"]
        checks[f"q3_{year}_denominator"] = not rows.empty and int(rows.iloc[0].denominator) == expected["q3"][year]["denominator"]
        checks[f"q3_{year}_median"] = not med_rows.empty and float(med_rows.iloc[0].value) == expected["q3"][year]["median"]
    disposition = build_population_disposition(frozen_dir)
    checks["population_disposition_rows"] = len(disposition) == 19280
    checks["population_disposition_no_unresolved"] = int((disposition.disposition == "UNRESOLVED").sum()) == 0
    checks["population_source_counts"] = disposition.source_system.value_counts().to_dict() == {"ORIGINAL": 15100, "SUPPLEMENTARY": 4180}
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise AssertionError("S6 independent verification failed: " + ", ".join(failed))
    return {"checks": checks, "manifest_version": manifest["manifest_version"]}
