import os
import pytest
import pandas as pd
from dirty_data.ingest import ingest_raw_data
from dirty_data.schema import get_expected_columns

def test_missing_source_file_fails():
    with pytest.raises(FileNotFoundError, match="Raw source file missing"):
        ingest_raw_data("non_existent_file.csv")

def test_correct_csv_loads(tmp_path):
    cols = get_expected_columns()
    df_expected = pd.DataFrame([["val"] * len(cols)], columns=cols)
    filepath = tmp_path / "valid.csv"
    df_expected.to_csv(filepath, index=False)
    
    df_actual = ingest_raw_data(str(filepath))
    assert len(df_actual) == 1
    assert list(df_actual.columns) == cols
    assert df_actual.iloc[0]["case_id"] == "val"

def test_missing_required_column_detected(tmp_path):
    cols = get_expected_columns()
    cols.remove("case_id")
    df_invalid = pd.DataFrame([["val"] * len(cols)], columns=cols)
    filepath = tmp_path / "missing_col.csv"
    df_invalid.to_csv(filepath, index=False)
    
    with pytest.raises(ValueError, match="Missing expected columns"):
        ingest_raw_data(str(filepath))

def test_duplicate_column_names_detected(tmp_path):
    cols = get_expected_columns()
    df_invalid = pd.DataFrame([["val"] * (len(cols) + 1)], columns=cols + ["case_id"])
    filepath = tmp_path / "dup_cols.csv"
    df_invalid.to_csv(filepath, index=False)
    
    with pytest.raises(ValueError, match="Duplicate columns detected"):
        ingest_raw_data(str(filepath))

def test_empty_input_handled(tmp_path):
    cols = get_expected_columns()
    df_empty = pd.DataFrame(columns=cols)
    filepath = tmp_path / "empty.csv"
    df_empty.to_csv(filepath, index=False)
    
    df_actual = ingest_raw_data(str(filepath))
    assert len(df_actual) == 0
    assert list(df_actual.columns) == cols

def test_raw_source_not_modified_by_ingestion(tmp_path):
    cols = get_expected_columns()
    df_source = pd.DataFrame([["01-02-2023"] * len(cols)], columns=cols)
    filepath = tmp_path / "source.csv"
    df_source.to_csv(filepath, index=False)
    
    orig_mtime = os.path.getmtime(filepath)
    with open(filepath, "r") as f:
        orig_content = f.read()
        
    df_actual = ingest_raw_data(str(filepath))
    
    assert os.path.getmtime(filepath) == orig_mtime
    with open(filepath, "r") as f:
        assert f.read() == orig_content
        
    assert df_actual.iloc[0]["intake_date"] == "01-02-2023"

def test_empty_fields_preserved_as_empty_strings(tmp_path):
    cols = get_expected_columns()
    df_source = pd.DataFrame([[""] * len(cols)], columns=cols)
    filepath = tmp_path / "empty_fields.csv"
    df_source.to_csv(filepath, index=False)
    
    df_actual = ingest_raw_data(str(filepath))
    assert df_actual.iloc[0]["priority"] == ""

def test_na_string_preserved_literally(tmp_path):
    cols = get_expected_columns()
    df_source = pd.DataFrame([["NA"] * len(cols)], columns=cols)
    filepath = tmp_path / "na_fields.csv"
    df_source.to_csv(filepath, index=False)
    
    df_actual = ingest_raw_data(str(filepath))
    assert df_actual.iloc[0]["priority"] == "NA"
