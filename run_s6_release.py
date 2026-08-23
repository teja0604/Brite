"""Official artifact-only S6 release runner."""
import json
from pathlib import Path

from dirty_data.s6_artifact_contract import validate_frozen_artifacts
from dirty_data.s6_execution import execute
from dirty_data.s6_population import build_population_disposition
from dirty_data.s6_release_verifier_v3 import verify


def main():
    validate_frozen_artifacts()
    out = Path("outputs/s6")
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in execute().items():
        frame.to_csv(out / f"{name}.csv", index=False)
    disposition = build_population_disposition()
    disposition.to_csv("outputs/s6_population_disposition.csv", index=False)
    result = verify()
    (out / "verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("S6 release verification passed")


if __name__ == "__main__":
    main()
