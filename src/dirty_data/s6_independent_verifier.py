"""Independent S6 verifier.

This module does not import analytics.py or any S6 runner.  It independently
derives the primary and secondary metrics from frozen evidence artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .contract import analyze_date_format


def _date(value):
    value = "" if value is None else str(value)
    if not value or analyze_date_format(value) in {"INVALID_DATE", "AMBIGUOUS_DATE_FORMAT"}:
        return pd.NaT
    try:
        return pd.to_datetime(value, dayfirst=False)
    except Exception:
        return pd.NaT


def _load(root, name, manifest):
    return pd.DataFrame(json.loads((root / manifest["artifacts"][name]["filename"]).read_text(encoding="utf-8")))


def independently_calculate(root="outputs/frozen"):
    root = Path(root)
    manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
    rec = _load(root, "s5_reconciled", manifest)
    identity = _load(root, "s3_identity_index", manifest)
    comparison = _load(root, "s4_comparison", manifest)
    ids = {str(r["case_id"]): r for r in identity.to_dict("records")}
    invalid = comparison[comparison["comparison_result"] == "INVALID_COMPARISON"]
    invalid_keys = {
        (str(r["case_id"]), str(r["original_source_row"]), str(r["supplementary_source_row"]), str(r["field_name"]))
        for r in invalid.to_dict("records")
    }
    rows = []
    for row in rec.to_dict("records"):
        cid = str(row["case_id"])
        ident = ids[cid]
        original_count = int(ident["original_count"])
        cardinality = str(ident["cardinality"])
        population = "SUPPLEMENTARY_ONLY" if cardinality == "SUPPLEMENTARY_ONLY" else "MANY_TO_ONE_PHYSICAL" if cardinality == "MANY_TO_ONE" else "ORIGINAL_ONLY_AMBIGUOUS" if cardinality == "ORIGINAL_ONLY" and original_count > 1 else "PRIMARY_CASE"
        intake = _date(row.get("intake_date", ""))
        closure = _date(row.get("closure_date", ""))
        duration = (closure - intake).days if pd.notna(intake) and pd.notna(closure) else None
        key_base = (cid, str(row.get("original_source_row", "")), str(row.get("supplementary_source_row", "")))
        invalid_dates = any(key_base + (field,) in invalid_keys for field in ("intake_date", "closure_date"))
        if invalid_dates or duration is None or duration < 0:
            duration = None
        rows.append({
            "case_id": cid,
            "population": population,
            "cardinality": cardinality,
            "duration_days": duration,
            "is_closed": str(row.get("status", "")).strip().lower() == "closed",
            "intake_year": int(intake.year) if pd.notna(intake) else None,
            "district": str(row.get("district", "")),
            "category": str(row.get("category", "")),
            "priority": str(row.get("priority", "")),
        })
    obs = pd.DataFrame(rows)
    primary = obs[(obs.population == "PRIMARY_CASE") & obs.is_closed & obs.duration_days.notna()]
    def metric(data):
        durations = data.duration_days.astype(int)
        return {"numerator": int((durations <= 30).sum()), "denominator": int(len(durations)), "median": float(durations.median()) if len(durations) else None}
    q1 = metric(primary)
    q3 = {str(year): metric(primary[(primary.priority.str.lower() == "high") & (primary.intake_year == year)]) for year in (2024, 2025)}
    return {"q1": q1, "q3": q3, "primary_observations": len(primary), "many_to_one_rows": int((obs.population == "MANY_TO_ONE_PHYSICAL").sum()), "supplementary_only_rows": int((obs.population == "SUPPLEMENTARY_ONLY").sum())}
