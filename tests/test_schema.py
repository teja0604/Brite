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

def test_canonical_schema_concepts():
    expected_canonical_fields = [
        'case_id', 'client_ref', 'district', 'intake_date', 'closure_date',
        'status', 'category', 'priority', 'caseworker_id', 'contact_count',
        'extract_date', 'source_system'
    ]
    actual = get_expected_columns('canonical')
    assert set(expected_canonical_fields) == set(actual)

def test_canonical_schema_properties():
    from dirty_data.schema import CANONICAL_SCHEMA
    # 2. case_id is the canonical identity field
    assert CANONICAL_SCHEMA['case_id']['nullable'] is False
    assert CANONICAL_SCHEMA['case_id']['source_mapping'] == ['case_id', 'reference']

    # 3. Mappings can conceptually target the same fields
    assert 'district' in CANONICAL_SCHEMA['district']['source_mapping']
    assert 'office' in CANONICAL_SCHEMA['district']['source_mapping']

    # 4. status is represented as a derived canonical concept
    assert CANONICAL_SCHEMA['status']['derived'] is True

    # 5. contact_count can remain unavailable
    assert CANONICAL_SCHEMA['contact_count']['unavailable_allowed'] is True
    assert CANONICAL_SCHEMA['contact_count']['type'] == 'string' # 6. Not numeric zero

    # 7. extract_date can be represented as unknown (nullable/unavailable allowed)
    assert CANONICAL_SCHEMA['extract_date']['nullable'] is True
    assert CANONICAL_SCHEMA['extract_date']['unavailable_allowed'] is True

    # 8. source_system distinguishes Original from Supplementary
    assert CANONICAL_SCHEMA['source_system']['derived'] is True
    assert CANONICAL_SCHEMA['source_system']['role'] == 'metadata'
    assert CANONICAL_SCHEMA['source_system']['nullable'] is False

    # 9. No source precedence encoded in model
    for field in CANONICAL_SCHEMA.values():
        assert 'precedence' not in field
        assert 'wins' not in field.get('semantic', '').lower()

