ORIGINAL_SCHEMA = {
    "case_id": {"semantic": "The case reference as recorded in the source system.", "type": "string", "nullable": False, "role": "identifying"},
    "client_ref": {"semantic": "Client name as recorded. Synthetic.", "type": "string", "nullable": True, "role": "identifying"},
    "district": {"semantic": "One of four district offices.", "type": "string", "nullable": True, "role": "analytical", "controlled_values": ["Calder Central", "Northgate", "Weybridge", "Ash Hill"]},
    "intake_date": {"semantic": "When the case was opened.", "type": "string", "nullable": True, "role": "operational"},
    "closure_date": {"semantic": "When the case was closed. Empty where the case is still open.", "type": "string", "nullable": True, "role": "operational"},
    "status": {"semantic": "Open or Closed.", "type": "string", "nullable": True, "role": "operational", "controlled_values": ["Open", "Closed"]},
    "category": {"semantic": "The case type.", "type": "string", "nullable": True, "role": "analytical"},
    "priority": {"semantic": "Priority band, where recorded.", "type": "string", "nullable": True, "role": "analytical"},
    "caseworker_id": {"semantic": "The assigned caseworker.", "type": "string", "nullable": True, "role": "operational"},
    "contact_count": {"semantic": "Number of recorded contacts on the case.", "type": "string", "nullable": True, "role": "analytical"}
}

SUPPLEMENTARY_SCHEMA = {
    "reference": {"semantic": "The case reference as recorded in the supplementary source.", "type": "string", "nullable": False, "role": "identifying"},
    "office": {"semantic": "One of the district offices.", "type": "string", "nullable": True, "role": "analytical"},
    "opened": {"semantic": "When the case was opened.", "type": "string", "nullable": True, "role": "operational"},
    "closed": {"semantic": "When the case was closed. Empty where the case is still open.", "type": "string", "nullable": True, "role": "operational"},
    "case_type": {"semantic": "The case type.", "type": "string", "nullable": True, "role": "analytical"},
    "band": {"semantic": "Priority band, where recorded.", "type": "string", "nullable": True, "role": "analytical"},
    "worker": {"semantic": "The assigned caseworker.", "type": "string", "nullable": True, "role": "operational"},
    "extract_date": {"semantic": "Date of the extract (2026-01-14).", "type": "string", "nullable": False, "role": "metadata"}
}

CANONICAL_SCHEMA = {
    "case_id": {
        "semantic": "The unified case identifier.",
        "type": "string",
        "nullable": False,
        "derived": False,
        "source_mapping": ["case_id", "reference"]
    },
    "client_ref": {
        "semantic": "Client name or reference. May be unavailable if source lacks it.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "unavailable_allowed": True,
        "source_mapping": ["client_ref"]
    },
    "district": {
        "semantic": "District office.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "source_mapping": ["district", "office"]
    },
    "intake_date": {
        "semantic": "Date case was opened.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "source_mapping": ["intake_date", "opened"]
    },
    "closure_date": {
        "semantic": "Date case was closed. Empty means open.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "source_mapping": ["closure_date", "closed"]
    },
    "status": {
        "semantic": "Open or Closed. Derived conceptually from closure_date presence.",
        "type": "string",
        "nullable": True,
        "derived": True,
        "unavailable_allowed": True,
        "source_mapping": ["status"]
    },
    "category": {
        "semantic": "The case type.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "source_mapping": ["category", "case_type"]
    },
    "priority": {
        "semantic": "Priority band.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "source_mapping": ["priority", "band"]
    },
    "caseworker_id": {
        "semantic": "Assigned caseworker.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "source_mapping": ["caseworker_id", "worker"]
    },
    "contact_count": {
        "semantic": "Number of contacts.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "unavailable_allowed": True,
        "source_mapping": ["contact_count"]
    },
    "extract_date": {
        "semantic": "Date the source was extracted. Unknown if not supplied.",
        "type": "string",
        "nullable": True,
        "derived": False,
        "unavailable_allowed": True,
        "role": "metadata",
        "source_mapping": ["extract_date"]
    },
    "source_system": {
        "semantic": "The origin of this canonical record (e.g. Original or Supplementary).",
        "type": "string",
        "nullable": False,
        "derived": True,
        "role": "metadata"
    }
}

def get_expected_columns(schema_type="original"):
    if schema_type == "original":
        return list(ORIGINAL_SCHEMA.keys())
    elif schema_type == "supplementary":
        return list(SUPPLEMENTARY_SCHEMA.keys())
    elif schema_type == "canonical":
        return list(CANONICAL_SCHEMA.keys())
    raise ValueError(f"Unknown schema type: {schema_type}")
