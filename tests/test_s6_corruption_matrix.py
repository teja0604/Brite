from pathlib import Path

import pandas as pd
import pytest

from dirty_data.s6_release_verifier_v3 import verify


def _copy_outputs(target):
    target.mkdir()
    for path in Path("outputs/s6").glob("*.csv"):
        (target / path.name).write_bytes(path.read_bytes())
    # Also copy the population disposition file as verifier expects it in the output path or current directory
    disp = Path("outputs/s6_population_disposition.csv")
    if disp.exists():
        (target / disp.name).write_bytes(disp.read_bytes())


@pytest.mark.parametrize("filename,selector,column", [
    ("exclusions.csv", None, None), # Exclusions removal
    ("q3.csv", ("2024", "30_DAY_CLOSURE_RATE"), "denominator"), # Q3 denominator
    ("q3.csv", ("2025", "30_DAY_CLOSURE_RATE"), "numerator"), # Q3 numerator
    ("observations.csv", ("MANY_TO_ONE_PHYSICAL", None), None), # MANY_TO_ONE count
    ("observations.csv", ("SUPPLEMENTARY_ONLY", None), None), # Supplementary-only count
    ("q1.csv", ("ALL", "30_DAY_CLOSURE_RATE"), "denominator"), # Q1 denominator
    ("q1.csv", ("ALL", "30_DAY_CLOSURE_RATE"), "numerator"), # Q1 numerator
])
def test_verifier_detects_population_and_exclusion_corruption(tmp_path, filename, selector, column):
    target = tmp_path / "s6"
    _copy_outputs(target)
    
    # The verifier reads from production_dir="outputs/s6" and frozen_dir="outputs/frozen".
    # We will pass absolute paths.
    production_dir = target
    frozen_dir = Path("outputs/frozen").absolute()
    
    path = production_dir / filename
    frame = pd.read_csv(path)
    if filename == "exclusions.csv":
        frame = frame.iloc[:-1]
    elif filename in ["q1.csv", "q3.csv"]:
        mask = (frame.segment.astype(str) == str(selector[0])) & (frame.metric == selector[1])
        frame.loc[mask, column] = frame.loc[mask, column] + 1
    else:
        frame = frame[frame.population != selector[0]]
    frame.to_csv(path, index=False)
    
    with pytest.raises(AssertionError):
        # We run the verifier with our corrupted output directory and the original frozen directory
        
        # We need to temporarily set the CWD or patch the "outputs/s6_population_disposition.csv" path in v3
        # because v3 does: disposition = pd.read_csv("outputs/s6_population_disposition.csv")
        # without using production_dir.
        import os
        original_cwd = os.getcwd()
        try:
            # We mock the outputs/ directory inside tmp_path
            mock_outputs = tmp_path / "outputs"
            mock_outputs.mkdir()
            mock_s6 = mock_outputs / "s6"
            mock_s6.mkdir()
            for p in production_dir.glob("*"):
                (mock_s6 / p.name).write_bytes(p.read_bytes())
            
            # The verifier also expects "outputs/s6_population_disposition.csv"
            disp = production_dir / "s6_population_disposition.csv"
            if disp.exists():
                (mock_outputs / "s6_population_disposition.csv").write_bytes(disp.read_bytes())
                
            os.chdir(str(tmp_path))
            verify(production_dir="outputs/s6", frozen_dir=str(frozen_dir))
        finally:
            os.chdir(original_cwd)
