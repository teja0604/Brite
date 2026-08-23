import pytest
from dirty_data.schema import ORIGINAL_SCHEMA, SUPPLEMENTARY_SCHEMA, get_expected_columns

def test_original_schema_contains_required_fields():
    expected_original_fields = [
        "case_id", "client_ref", "district", "intake_date",
        "closure_date", "status", "category", "priority",
        "caseworker_id", "contact_count"
    ]
    actual_fields = get_expected_columns("original")
    assert set(expected_original_fields) == set(actual_fields)
    assert ORIGINAL_SCHEMA["case_id"]["role"] == "identifying"

def test_supplementary_schema_contains_required_fields():
    expected_supp_fields = [
        "reference", "office", "opened", "closed", 
        "case_type", "band", "worker", "extract_date"
    ]
    actual_fields = get_expected_columns("supplementary")
    assert set(expected_supp_fields) == set(actual_fields)

def test_supplementary_schema_roles_and_types():
    assert SUPPLEMENTARY_SCHEMA["reference"]["role"] == "identifying"
    assert SUPPLEMENTARY_SCHEMA["extract_date"]["role"] == "metadata"
    assert SUPPLEMENTARY_SCHEMA["opened"]["role"] == "operational"
    assert SUPPLEMENTARY_SCHEMA["closed"]["role"] == "operational"
    
def test_schema_fetching_invalid_type():
    with pytest.raises(ValueError, match="Unknown schema type"):
        get_expected_columns("invalid_schema_type")
