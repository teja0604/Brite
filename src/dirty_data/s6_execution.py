"""Release S6 execution entry point; imports no S2-S5 implementation modules."""
from __future__ import annotations

import pandas as pd

from .s6_analytics import _summary, evaluate_frozen, load_frozen_artifacts


def execute(directory="outputs/frozen"):
    artifacts = load_frozen_artifacts(directory)
    results = evaluate_frozen(artifacts)
    observations = results["observations"]
    high = observations[
        (observations["population"] == "PRIMARY_CASE")
        & observations["priority"].str.strip().str.lower().eq("high")
    ].copy()
    high["cohort"] = high["intake_year"].apply(lambda value: str(int(value)) if pd.notna(value) else "")
    results["q3"] = _summary(high, "PRIMARY_CASE", "cohort")
    results["q3"] = results["q3"][results["q3"]["segment"].isin(["2024", "2025"])]
    return results
