import pytest
import pandas as pd
import shutil
from pathlib import Path
from dirty_data.s6_release_verifier_v3 import verify

@pytest.mark.parametrize("filename,selector,column", [
    ("exclusions.csv", None, None), # Exclusions removal
    ("q3.csv", ("2024", "30_DAY_CLOSURE_RATE"), "denominator"), # Q3 denominator
    ("q3.csv", ("2025", "30_DAY_CLOSURE_RATE"), "numerator"), # Q3 numerator
    ("observations.csv", ("MANY_TO_ONE_PHYSICAL", None), None), # MANY_TO_ONE count
    ("observations.csv", ("SUPPLEMENTARY_ONLY", None), None), # Supplementary-only count
    ("q1.csv", ("ALL", "30_DAY_CLOSURE_RATE"), "denominator"), # Q1 denominator
    ("q1.csv", ("ALL", "30_DAY_CLOSURE_RATE"), "numerator"), # Q1 numerator
])
def test_verifier_detects_population_and_exclusion_corruption(tmp_path, s6_production_dir, s6_frozen_dir, filename, selector, column):
    target = tmp_path / "s6"
    target.mkdir()
    
    # Copy production outputs to isolated tmp directory
    for p in s6_production_dir.glob("*.csv"):
        shutil.copy2(p, target / p.name)
    (tmp_path / "outputs").mkdir()
    shutil.copy2(s6_production_dir.parent / "s6_population_disposition.csv", tmp_path / "outputs/s6_population_disposition.csv")
    
    path = target / filename
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
        verify(production_dir=str(target), frozen_dir=str(s6_frozen_dir), root=str(tmp_path))
