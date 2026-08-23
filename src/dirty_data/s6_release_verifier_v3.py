from __future__ import annotations

from pathlib import Path

import pandas as pd

from .s6_artifact_contract import validate_frozen_artifacts
from .s6_independent_verifier import independently_calculate


def verify(production_dir="outputs/s6", frozen_dir="outputs/frozen"):
    manifest = validate_frozen_artifacts(frozen_dir)
    expected = independently_calculate(frozen_dir)
    out = Path(production_dir)
    q1 = pd.read_csv(out / "q1.csv")
    q3 = pd.read_csv(out / "q3.csv")
    observations = pd.read_csv(out / "observations.csv")
    exclusions = pd.read_csv(out / "exclusions.csv")
    disposition = pd.read_csv("outputs/s6_population_disposition.csv")
    rate = q1[(q1.metric == "30_DAY_CLOSURE_RATE") & (q1.segment == "ALL")].iloc[0]
    median = q1[(q1.metric == "MEDIAN_CLOSURE_DURATION") & (q1.segment == "ALL")].iloc[0]
    checks = {
        "q1_numerator": int(rate.numerator) == expected["q1"]["numerator"],
        "q1_denominator": int(rate.denominator) == expected["q1"]["denominator"],
        "q1_rate": abs(float(rate.value) - expected["q1"]["numerator"] / expected["q1"]["denominator"]) < 1e-12,
        "q1_median": float(median.value) == expected["q1"]["median"],
        "many_to_one_rows": int((observations.population == "MANY_TO_ONE_PHYSICAL").sum()) == expected["many_to_one_rows"],
        "supplementary_only_rows": int((observations.population == "SUPPLEMENTARY_ONLY").sum()) == expected["supplementary_only_rows"],
        "invalid_comparison_rows": len(exclusions) == 762 and set(exclusions["comparison_result"]) == {"INVALID_COMPARISON"},
        "disposition_rows": len(disposition) == 19280,
        "disposition_original": int((disposition.source_system == "ORIGINAL").sum()) == 15100,
        "disposition_supplementary": int((disposition.source_system == "SUPPLEMENTARY").sum()) == 4180,
        "disposition_unresolved": int((disposition.disposition == "UNRESOLVED").sum()) == 0,
    }
    q3_segment = q3.segment.astype(str).str.replace(r"\.0$", "", regex=True)
    for year in ("2024", "2025"):
        rows = q3[(q3.metric == "30_DAY_CLOSURE_RATE") & (q3_segment == year)]
        med_rows = q3[(q3.metric == "MEDIAN_CLOSURE_DURATION") & (q3_segment == year)]
        checks[f"q3_{year}_numerator"] = not rows.empty and int(rows.iloc[0].numerator) == expected["q3"][year]["numerator"]
        checks[f"q3_{year}_denominator"] = not rows.empty and int(rows.iloc[0].denominator) == expected["q3"][year]["denominator"]
        checks[f"q3_{year}_rate"] = not rows.empty and abs(float(rows.iloc[0].value) - expected["q3"][year]["numerator"] / expected["q3"][year]["denominator"]) < 1e-12
        checks[f"q3_{year}_median"] = not med_rows.empty and float(med_rows.iloc[0].value) == expected["q3"][year]["median"]
    if not all(checks.values()):
        raise AssertionError("S6 independent verification failed: " + ", ".join(k for k, v in checks.items() if not v))
    return {"checks": checks, "manifest_version": manifest["manifest_version"]}
