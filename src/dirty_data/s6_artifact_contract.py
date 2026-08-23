from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPECTED_ZERO_ROW_SCHEMAS = {
    "s5_unresolved": ["case_id", "source_system", "source_row_index", "reason", "rule_applied"],
}


def validate_frozen_artifacts(root="outputs/frozen"):
    root = Path(root)
    manifest_path = root / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    for name, info in manifest["artifacts"].items():
        path = root / info["filename"]
        if not path.exists():
            errors.append(f"missing artifact: {name}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != info["sha256"]:
            errors.append(f"hash mismatch: {name}")
        records = json.loads(path.read_text(encoding="utf-8"))
        if len(records) != info["row_count"]:
            errors.append(f"row count mismatch: {name}")
        actual_columns = list(records[0].keys()) if records else EXPECTED_ZERO_ROW_SCHEMAS.get(name, info.get("columns", []))
        expected_columns = EXPECTED_ZERO_ROW_SCHEMAS.get(name, info.get("columns", []))
        if set(actual_columns) != set(expected_columns):
            errors.append(f"schema mismatch: {name}")
    if errors:
        raise ValueError("; ".join(errors))
    return manifest
