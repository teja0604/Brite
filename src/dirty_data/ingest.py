import os
import csv
import pandas as pd
from .schema import get_expected_columns

def ingest_raw_data(filepath: str) -> pd.DataFrame:
    """
    Reads the raw CSV deterministically without analytical cleaning.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Raw source file missing: {filepath}")
        
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
            if len(header) != len(set(header)):
                raise ValueError("Duplicate columns detected in raw data.")
        except StopIteration:
            pass # Empty file handled by pandas
        
    # Read everything as strings to prevent silent coercion (e.g. date parsing or dropping leading zeros)
    # keep_default_na=False ensures empty fields are preserved as empty strings, and 'NA' remains 'NA'.
    df = pd.read_csv(filepath, dtype=str, keep_default_na=False)
    
    expected_cols = get_expected_columns()
    actual_cols = list(df.columns)
        
    if not set(expected_cols).issubset(set(actual_cols)):
        missing = set(expected_cols) - set(actual_cols)
        raise ValueError(f"Missing expected columns: {missing}")
        
    return df
