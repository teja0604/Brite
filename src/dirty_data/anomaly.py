from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

class AnomalyType(Enum):
    MISSING_VALUE = "MISSING_VALUE"
    INVALID_DOMAIN = "INVALID_DOMAIN"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CANDIDATE_IDENTITY_VARIANT = "CANDIDATE_IDENTITY_VARIANT"
    CANDIDATE_CATEGORY_VARIANT = "CANDIDATE_CATEGORY_VARIANT"
    DATE_FORMAT_VARIATION = "DATE_FORMAT_VARIATION"
    AMBIGUOUS_DATE_FORMAT = "AMBIGUOUS_DATE_FORMAT"
    INVALID_DATE = "INVALID_DATE"
    LOGICAL_CONTRADICTION = "LOGICAL_CONTRADICTION"

class Severity(Enum):
    CRITICAL = "CRITICAL" # The record cannot safely participate in a specific analysis without resolution
    HIGH = "HIGH"         # Likely affects an operational question or creates strong analytical risk
    MEDIUM = "MEDIUM"     # Requires correction but may not invalidate the record
    LOW = "LOW"           # Suspicious/candidate issue requiring review

@dataclass
class Anomaly:
    source_row: int
    case_id: str
    field: str
    anomaly_type: AnomalyType
    severity: Severity
    observed_value: Any
    evidence: str
    normalized_signature: Optional[str] = None
