"""Create the frozen S2-S5 evidence package used by S6.

This module is intentionally the only place in the S6 workflow that invokes
the upstream phases.  S6 itself consumes the resulting JSON artifacts only.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

from .adapter import adapt_original_to_canonical, adapt_supplementary_to_canonical
from .compare import compare_fields
from .identity import match_identities
from .reconcile import reconcile_dataset


ARTIFACTS = {
    "s2_original_canonical": "s2_original_canonical.json",
    "s2_supplementary_canonical": "s2_supplementary_canonical.json",
    "s3_aligned": "s3_aligned.json",
    "s3_identity_index": "s3_identity_index.json",
    "s4_comparison": "s4_comparison.json",
    "s5_reconciled": "s5_reconciled.json",
    "s5_unresolved": "s5_unresolved.json",
    "s5_audit": "s5_audit.json",
}


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _write_json(path: Path, records: list[dict]) -> str:
    payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(payload + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_artifacts(output_dir: str | Path = "outputs/frozen") -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    original_path = Path("data/raw/case-export-2023-2025.csv")
    supplementary_path = Path("data/raw/2 - Dirty Data, Real Decisions/case-export-supplementary.csv")
    original = pd.read_csv(original_path, dtype=str, keep_default_na=False)
    supplementary = pd.read_csv(supplementary_path, dtype=str, keep_default_na=False)

    original_canonical = adapt_original_to_canonical(original)
    supplementary_canonical = adapt_supplementary_to_canonical(supplementary)
    aligned, identity_index, metrics = match_identities(original_canonical, supplementary_canonical)
    comparison = compare_fields(aligned, identity_index)
    reconciled, unresolved, audit = reconcile_dataset(aligned, identity_index, comparison)

    frames = {
        "s2_original_canonical": original_canonical,
        "s2_supplementary_canonical": supplementary_canonical,
        "s3_aligned": aligned,
        "s3_identity_index": identity_index,
        "s4_comparison": comparison,
        "s5_reconciled": reconciled,
        "s5_unresolved": unresolved,
        "s5_audit": audit,
    }
    manifest = {
        "manifest_version": "S6-1",
        "creation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_hashes": {
            "original": hashlib.sha256(original_path.read_bytes()).hexdigest(),
            "supplementary": hashlib.sha256(supplementary_path.read_bytes()).hexdigest(),
        },
        "identity_metrics": metrics,
        "artifacts": {},
    }
    dependencies = {
        "s2_original_canonical": ["original"],
        "s2_supplementary_canonical": ["supplementary"],
        "s3_aligned": ["s2_original_canonical", "s2_supplementary_canonical"],
        "s3_identity_index": ["s2_original_canonical", "s2_supplementary_canonical"],
        "s4_comparison": ["s3_aligned", "s3_identity_index"],
        "s5_reconciled": ["s3_aligned", "s3_identity_index", "s4_comparison"],
        "s5_unresolved": ["s3_aligned", "s3_identity_index", "s4_comparison"],
        "s5_audit": ["s3_aligned", "s3_identity_index", "s4_comparison"],
    }
    for name, frame in frames.items():
        filename = ARTIFACTS[name]
        digest = _write_json(output / filename, _records(frame))
        manifest["artifacts"][name] = {
            "phase": name[:2].upper(),
            "filename": filename,
            "schema_version": "canonical-v2" if name.startswith("s2_") else "evidence-v1",
            "row_count": len(frame),
            "columns": list(frame.columns),
            "sha256": digest,
            "source_dependencies": dependencies[name],
            "provenance_columns": [c for c in frame.columns if "source" in c or "extract" in c or c == "case_id"],
        }
    manifest_path = output / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(freeze_artifacts(), indent=2, sort_keys=True))
