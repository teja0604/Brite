from pathlib import Path

import pandas as pd
import pytest

from dirty_data.s6_release_verifier_v2 import verify


@pytest.mark.parametrize("field", ["numerator", "denominator", "value"])
def test_independent_verifier_detects_corrupted_output(tmp_path, field):
    target = tmp_path / "s6"
    target.mkdir()
    for path in Path("outputs/s6").glob("*.csv"):
        (target / path.name).write_bytes(path.read_bytes())
    q1_path = target / "q1.csv"
    q1 = pd.read_csv(q1_path)
    q1.loc[(q1.metric == "30_DAY_CLOSURE_RATE") & (q1.segment == "ALL"), field] = 999999
    q1.to_csv(q1_path, index=False)
    with pytest.raises(AssertionError):
        verify(target)
