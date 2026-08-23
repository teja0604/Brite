import pytest

from dirty_data.freeze_artifacts import freeze_artifacts as freeze
from dirty_data.s6_execution import execute


@pytest.fixture(scope="session")
def s6_frozen_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("outputs")
    freeze(output_dir=root / "frozen")
    return root / "frozen"


@pytest.fixture(scope="session")
def s6_production_dir(tmp_path_factory, s6_frozen_dir):
    root = s6_frozen_dir.parent
    out = root / "s6"
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in execute(directory=str(s6_frozen_dir)).items():
        frame.to_csv(out / f"{name}.csv", index=False)

    # Also write population disposition, since verifier expects it.
    from dirty_data.s6_population import build_population_disposition
    disposition = build_population_disposition(directory=str(s6_frozen_dir))
    disposition.to_csv(root / "s6_population_disposition.csv", index=False)

    return out
