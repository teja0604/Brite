from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .s6_analytics import build_observations, load_frozen_artifacts


def build_population_disposition(directory="outputs/frozen"):
    artifacts = load_frozen_artifacts(directory)
    observations, _ = build_observations(artifacts)
    aligned = artifacts["s3_aligned"]
    identity = {str(r["case_id"]): r for r in artifacts["s3_identity_index"].to_dict("records")}
    by_original = {}
    by_supplementary = {}
    for row in observations.to_dict("records"):
        for key, target in [("original_source_row", by_original), ("supplementary_source_row", by_supplementary)]:
            value = str(row.get(key, ""))
            if value:
                target.setdefault(value, []).append(row)

    records = []
    for row in aligned.to_dict("records"):
        source = str(row["source_system"])
        source_row = str(row["source_row_index"])
        cid = str(row["case_id"])
        matches = (by_original if source == "ORIGINAL" else by_supplementary).get(source_row, [])
        ident = identity[cid]
        if not matches:
            disposition = "UNRESOLVED"
            reason = "No reconciled representation found for physical source row"
            included_q1 = False
            included_q3 = False
            population = "UNRESOLVED_SOURCE_ROW"
        else:
            dispositions = {str(m["disposition"]) for m in matches}
            disposition = "INCLUDED" if "INCLUDED" in dispositions else "SEPARATE_POPULATION" if "SEPARATE_POPULATION" in dispositions else "EXCLUDED_WITH_REASON"
            reason = "; ".join(sorted({str(m["disposition_reason"]) for m in matches}))
            included_q1 = any(m["disposition"] == "INCLUDED" for m in matches)
            included_q3 = any(m["disposition"] == "INCLUDED" and m["priority"].strip().lower() == "high" and m["intake_year"] in (2024, 2025) for m in matches)
            population = str(matches[0]["population"])
        records.append({
            "source_system": source,
            "source_row_index": source_row,
            "case_id": cid,
            "cardinality": str(ident["cardinality"]),
            "population": population,
            "disposition": disposition,
            "reason": reason,
            "included_in_q1": included_q1,
            "included_in_q3": included_q3,
            "provenance": json.dumps({"case_id": cid, "source_system": source, "source_row_index": source_row}, sort_keys=True),
        })
    return pd.DataFrame(records)
