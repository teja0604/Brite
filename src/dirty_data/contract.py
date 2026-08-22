import re
from typing import Set
from datetime import datetime

ALLOWED_DISTRICTS: Set[str] = {"Calder Central", "Northgate", "Weybridge", "Ash Hill"}
ALLOWED_STATUSES: Set[str] = {"Open", "Closed"}

def analyze_date_format(date_str: str) -> str:
    """
    Analyzes a date string and returns a classification:
    - CANONICAL: strictly YYYY-MM-DD and physically valid.
    - AMBIGUOUS_DATE_FORMAT: numeric date where month/day ordering is ambiguous (e.g. 03/04/2024).
    - DATE_FORMAT_VARIATION: unambiguous non-canonical but valid date.
    - INVALID_DATE: cannot be parsed as a calendar date.
    """
    is_canonical = bool(re.match(r"^\d{4}-\d{2}-\d{2}$", date_str))
    
    if is_canonical:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return "CANONICAL"
        except ValueError:
            return "INVALID_DATE"
            
    # Check explicit textual format (e.g., "May 17, 2024")
    try:
        datetime.strptime(date_str, "%B %d, %Y")
        return "DATE_FORMAT_VARIATION"
    except ValueError:
        pass
            
    # Check for ambiguous numeric formats (e.g., 03/04/2024 or 03-04-2024)
    match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", date_str)
    if match:
        p1, p2, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        
        p1_could_be_month = (1 <= p1 <= 12)
        p2_could_be_month = (1 <= p2 <= 12)
        
        if p1_could_be_month and p2_could_be_month:
            return "AMBIGUOUS_DATE_FORMAT"
            
        if not p1_could_be_month and not p2_could_be_month:
            return "INVALID_DATE"
            
        # One is definitely the month, the other is the day
        if p1_could_be_month:
            month, day = p1, p2
        else:
            month, day = p2, p1
            
        try:
            datetime(year, month, day)
            return "DATE_FORMAT_VARIATION"
        except ValueError:
            return "INVALID_DATE"
            
    return "INVALID_DATE"

def is_numeric_string(val_str: str) -> bool:
    if val_str == "":
        return True
    return val_str.isdigit()

def normalize_string_signature(val_str: str) -> str:
    """
    Creates a deterministic normalization signature.
    - trims whitespace
    - lowercases
    - collapses internal whitespace
    - removes non-alphanumeric (or keeps alphanumeric and spaces)
    """
    if val_str == "":
        return ""
    s = val_str.lower()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()
