"""Pure consumer of frozen S2-S5 artifacts for Phase S6."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .contract import analyze_date_format
from .s6_policy import POLICY_IDS


BUSINESS_FIELDS = ["client_ref", "district", "intake_date", "closure_date", "status", "category", "priority", "caseworker_id", "contact_count"]


def _load(path: Path) -> pd.DataFrame:
    return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))


def load_frozen_artifacts(directory: str | Path = "outputs/frozen") -> dict[str, pd.DataFrame]:
    root = Path(directory)
    manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
    result = {name: _load(root / info["filename"]) for name, info in manifest["artifacts"].items()}
    result["_manifest"] = manifest
    return result


def _date(value: object) -> pd.Timestamp:
    value = "" if value is None else str(value)
    if not value or analyze_date_format(value) in {"INVALID_DATE", "AMBIGUOUS_DATE_FORMAT"}:
        return pd.NaT
    try:
        return pd.to_datetime(value, format="%Y-%m-%d" if analyze_date_format(value) == "CANONICAL" else None, dayfirst=False)
    except Exception:
        return pd.NaT


def _invalid_map(comparison: pd.DataFrame) -> dict[tuple[str, str, str, str], list[dict]]:
    invalid = comparison[comparison["comparison_result"] == "INVALID_COMPARISON"]
    result: dict[tuple[str, str, str, str], list[dict]] = {}
    for row in invalid.to_dict("records"):
        key = (str(row["case_id"]), str(row["original_source_row"]), str(row["supplementary_source_row"]), str(row["field_name"]))
        result.setdefault(key, []).append(row)
    return result


def _identity_map(index: pd.DataFrame) -> dict[str, dict]:
    return {str(row["case_id"]): row for row in index.to_dict("records")}


def build_observations(artifacts: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rec = artifacts["s5_reconciled"].copy()
    index = _identity_map(artifacts["s3_identity_index"])
    comparison = artifacts["s4_comparison"]
    invalid = _invalid_map(comparison)
    observations = []
    exclusions = []

    for row in rec.to_dict("records"):
        cid = str(row.get("case_id", ""))
        identity = index.get(cid, {})
        cardinality = str(identity.get("cardinality", "UNKNOWN"))
        original_count = int(identity.get("original_count", 0) or 0)
        supplementary_count = int(identity.get("supplementary_count", 0) or 0)
        original_row = str(row.get("original_source_row", ""))
        supplementary_row = str(row.get("supplementary_source_row", ""))
        if cardinality == "SUPPLEMENTARY_ONLY":
            population = "SUPPLEMENTARY_ONLY"
        elif cardinality == "MANY_TO_ONE":
            population = "MANY_TO_ONE_PHYSICAL"
        elif cardinality == "ORIGINAL_ONLY" and original_count > 1:
            population = "ORIGINAL_ONLY_AMBIGUOUS"
        else:
            population = "PRIMARY_CASE"

        base = {
            "case_id": cid,
            "original_source_row": original_row,
            "supplementary_source_row": supplementary_row,
            "cardinality": cardinality,
            "s5_reconciliation_decision": str(row.get("reconciliation_status", "")),
            "population": population,
            "disposition": "INCLUDED",
            "disposition_reason": "Eligible for applicable analytical population",
            "policy_id": POLICY_IDS["primary_metric"],
        }
        intake = _date(row.get("intake_date", ""))
        closure = _date(row.get("closure_date", ""))
        duration = (closure - intake).days if pd.notna(intake) and pd.notna(closure) else None
        if duration is not None and duration < 0:
            duration = None
        base.update({
            "intake_year": int(intake.year) if pd.notna(intake) else None,
            "duration_days": duration,
            "is_closed": str(row.get("status", "")).strip().lower() == "closed",
            "district": str(row.get("district", "")),
            "category": str(row.get("category", "")),
            "priority": str(row.get("priority", "")),
        })

        invalid_rows = []
        for field in ("intake_date", "closure_date"):
            key = (cid, original_row, supplementary_row, field)
            invalid_rows.extend(invalid.get(key, []))
        if invalid_rows:
            for bad in invalid_rows:
                exclusions.append({
                    **base,
                    "field": bad["field_name"],
                    "original_value": bad["original_value"],
                    "supplementary_value": bad["supplementary_value"],
                    "comparison_result": "INVALID_COMPARISON",
                    "reason": bad["comparison_reason"],
                    "rule_policy_id": POLICY_IDS["invalid_comparison"],
                    "disposition": "EXCLUDED_WITH_REASON",
                })
            base["duration_days"] = None
            base["invalid_comparison"] = True
        else:
            base["invalid_comparison"] = False

        if population == "SUPPLEMENTARY_ONLY":
            base["disposition"] = "SEPARATE_POPULATION"
            base["disposition_reason"] = "Supplementary-only population is reported separately"
            base["policy_id"] = POLICY_IDS["supplementary_only"]
        elif population == "MANY_TO_ONE_PHYSICAL":
            base["disposition"] = "SEPARATE_POPULATION"
            base["disposition_reason"] = "MANY_TO_ONE physical sensitivity population"
            base["policy_id"] = POLICY_IDS["many_to_one"]
        elif population == "ORIGINAL_ONLY_AMBIGUOUS":
            base["disposition"] = "EXCLUDED_WITH_REASON"
            base["disposition_reason"] = "Original-only identity has multiple physical records and no unambiguous case record"
            base["policy_id"] = POLICY_IDS["many_to_one"]
        if not base["is_closed"]:
            base["disposition"] = "EXCLUDED_WITH_REASON" if population == "PRIMARY_CASE" else base["disposition"]
            base["disposition_reason"] = "Open case is not a valid closed-duration observation" if population == "PRIMARY_CASE" else base["disposition_reason"]
        elif base["duration_days"] is None and population == "PRIMARY_CASE":
            base["disposition"] = "EXCLUDED_WITH_REASON"
            base["disposition_reason"] = "Invalid or missing duration dates"
        observations.append(base)
    return pd.DataFrame(observations), pd.DataFrame(exclusions)


def _summary(observations: pd.DataFrame, population: str, group_field: str | None = None) -> pd.DataFrame:
    data = observations[(observations["population"] == population) & (observations["is_closed"]) & observations["duration_days"].notna()].copy()
    if group_field:
        groups = data.groupby(group_field, dropna=False)
    else:
        groups = [("ALL", data)]
    rows = []
    for key, group in groups:
        durations = group["duration_days"].astype(int)
        rows.append({
            "population": population,
            "segment": str(key),
            "metric": "30_DAY_CLOSURE_RATE",
            "numerator": int((durations <= 30).sum()),
            "denominator": int(len(durations)),
            "value": float((durations <= 30).mean()) if len(durations) else None,
            "unit": "rate",
            "policy_id": POLICY_IDS["primary_metric"],
        })
        rows.append({
            "population": population,
            "segment": str(key),
            "metric": "MEDIAN_CLOSURE_DURATION",
            "numerator": None,
            "denominator": int(len(durations)),
            "value": float(durations.median()) if len(durations) else None,
            "unit": "days",
            "policy_id": POLICY_IDS["secondary_metric"],
        })
    return pd.DataFrame(rows)


def evaluate_frozen(artifacts: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    observations, exclusions = build_observations(artifacts)
    primary = observations[observations["population"] == "PRIMARY_CASE"]
    supp = observations[observations["population"] == "SUPPLEMENTARY_ONLY"]
    many = observations[observations["population"] == "MANY_TO_ONE_PHYSICAL"]
    q1 = pd.concat([_summary(primary, "PRIMARY_CASE"), _summary(primary, "PRIMARY_CASE", "intake_year")], ignore_index=True)
    q2 = pd.concat([_summary(primary, "PRIMARY_CASE", "district"), _summary(primary, "PRIMARY_CASE", "category")], ignore_index=True)
    q3 = pd.concat([_summary(primary[primary["priority"].str.strip().str.lower() == "high"], "PRIMARY_CASE", "intake_year")], ignore_index=True)
    q3 = q3[q3["segment"].isin(["2024", "2025"])]
    supp_metrics = _summary(supp, "SUPPLEMENTARY_ONLY", "intake_year")
    many_metrics = _summary(many, "MANY_TO_ONE_PHYSICAL", "intake_year")
    return {"observations": observations, "exclusions": exclusions, "q1": q1, "q2": q2, "q3": q3, "supplementary_only": supp_metrics, "many_to_one_physical": many_metrics}
