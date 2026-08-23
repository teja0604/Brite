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
    "reference": {"semantic": "The case reference", "type": "string", "nullable": False, "role": "identifying"},
    "office": {"semantic": "The district office", "type": "string", "nullable": True, "role": "analytical"},
    "opened": {"semantic": "When the case was opened", "type": "string", "nullable": True, "role": "operational"},
    "closed": {"semantic": "When the case was closed", "type": "string", "nullable": True, "role": "operational"},
    "case_type": {"semantic": "The case type", "type": "string", "nullable": True, "role": "analytical"},
    "band": {"semantic": "Priority band", "type": "string", "nullable": True, "role": "analytical"},
    "worker": {"semantic": "The assigned caseworker", "type": "string", "nullable": True, "role": "operational"},
    "extract_date": {"semantic": "Date of export", "type": "string", "nullable": False, "role": "metadata"}
}

CANONICAL_SCHEMA = {
    "case_id": {"type": "string"},
    "client_ref": {"type": "string"},
    "district": {"type": "string"},
    "intake_date": {"type": "string"},
    "closure_date": {"type": "string"},
    "status": {"type": "string"},
    "category": {"type": "string"},
    "priority": {"type": "string"},
    "caseworker_id": {"type": "string"},
    "contact_count": {"type": "string"},
    "extract_date": {"type": "string"},
    "source_system": {"type": "string"}
}

def get_expected_columns(source: str = "original"):
    if source == "supplementary":
        return list(SUPPLEMENTARY_SCHEMA.keys())
    return list(ORIGINAL_SCHEMA.keys())
