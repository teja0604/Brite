RAW_SCHEMA = {
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

def get_expected_columns():
    return list(RAW_SCHEMA.keys())
