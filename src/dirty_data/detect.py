import pandas as pd
from typing import List
import re

from dirty_data.anomaly import Anomaly, AnomalyType, Severity
from dirty_data.contract import ALLOWED_DISTRICTS, ALLOWED_STATUSES, analyze_date_format, is_numeric_string, normalize_string_signature

def detect_anomalies(df: pd.DataFrame) -> List[Anomaly]:
    anomalies = []
    
    # 1. Pre-compute identities
    exact_case_counts = df[df["case_id"] != ""]["case_id"].value_counts().to_dict()
    
    id_sig_to_raw = {}
    for raw_id in df["case_id"].dropna().unique():
        if raw_id == "": continue
        sig = normalize_string_signature(raw_id)
        if sig not in id_sig_to_raw:
            id_sig_to_raw[sig] = set()
        id_sig_to_raw[sig].add(raw_id)
        
    # 2. Pre-compute category variants
    cat_sig_to_raw = {}
    for raw_cat in df["category"].dropna().unique():
        if raw_cat == "": continue
        sig = normalize_string_signature(raw_cat)
        if sig not in cat_sig_to_raw:
            cat_sig_to_raw[sig] = set()
        cat_sig_to_raw[sig].add(raw_cat)

    for i, row_tuple in enumerate(df.itertuples(index=False)):
        source_row = i + 1  # 1-based index excluding header
        row = row_tuple._asdict()
        
        def add_anomaly(field, a_type, severity, evidence, obs, sig=None):
            anomalies.append(Anomaly(
                source_row=source_row,
                case_id=row.get("case_id", ""),
                field=field,
                anomaly_type=a_type,
                severity=severity,
                observed_value=obs,
                evidence=evidence,
                normalized_signature=sig
            ))
            
        case_id = row.get("case_id", "")
        # Missingness
        if case_id == "":
            add_anomaly("case_id", AnomalyType.MISSING_VALUE, Severity.CRITICAL, "case_id is empty", "")
        if row.get("district", "") == "":
            add_anomaly("district", AnomalyType.MISSING_VALUE, Severity.HIGH, "district is empty", "")
        if row.get("intake_date", "") == "":
            add_anomaly("intake_date", AnomalyType.MISSING_VALUE, Severity.HIGH, "intake_date is empty", "")
        if row.get("status", "") == "":
            add_anomaly("status", AnomalyType.MISSING_VALUE, Severity.HIGH, "status is empty", "")
            
        # Invalid Domain
        district = row.get("district", "")
        if district != "" and district not in ALLOWED_DISTRICTS:
            add_anomaly("district", AnomalyType.INVALID_DOMAIN, Severity.HIGH, f"'{district}' not in allowed districts", district)
            
        status = row.get("status", "")
        if status != "" and status not in ALLOWED_STATUSES:
            add_anomaly("status", AnomalyType.INVALID_DOMAIN, Severity.HIGH, f"'{status}' not in allowed statuses", status)
            
        contact = row.get("contact_count", "")
        if contact != "" and not is_numeric_string(contact):
            add_anomaly("contact_count", AnomalyType.INVALID_DOMAIN, Severity.MEDIUM, "contact_count is not numeric", contact)
            
        # Date Format and Invalidity
        intake = row.get("intake_date", "")
        intake_canonical = False
        if intake != "":
            date_status = analyze_date_format(intake)
            if date_status == "INVALID_DATE":
                add_anomaly("intake_date", AnomalyType.INVALID_DATE, Severity.HIGH, "intake_date cannot be parsed as a valid calendar date", intake)
            elif date_status == "AMBIGUOUS_DATE_FORMAT":
                add_anomaly("intake_date", AnomalyType.AMBIGUOUS_DATE_FORMAT, Severity.MEDIUM, "intake_date is ambiguous (e.g. DD/MM vs MM/DD)", intake)
            elif date_status == "DATE_FORMAT_VARIATION":
                add_anomaly("intake_date", AnomalyType.DATE_FORMAT_VARIATION, Severity.MEDIUM, "intake_date is a valid date but not in canonical YYYY-MM-DD format", intake)
            elif date_status == "CANONICAL":
                intake_canonical = True
                
        closure = row.get("closure_date", "")
        closure_canonical = False
        if closure != "":
            date_status = analyze_date_format(closure)
            if date_status == "INVALID_DATE":
                add_anomaly("closure_date", AnomalyType.INVALID_DATE, Severity.HIGH, "closure_date cannot be parsed as a valid calendar date", closure)
            elif date_status == "AMBIGUOUS_DATE_FORMAT":
                add_anomaly("closure_date", AnomalyType.AMBIGUOUS_DATE_FORMAT, Severity.MEDIUM, "closure_date is ambiguous (e.g. DD/MM vs MM/DD)", closure)
            elif date_status == "DATE_FORMAT_VARIATION":
                add_anomaly("closure_date", AnomalyType.DATE_FORMAT_VARIATION, Severity.MEDIUM, "closure_date is a valid date but not in canonical YYYY-MM-DD format", closure)
            elif date_status == "CANONICAL":
                closure_canonical = True
            
        # Logical Contradictions
        if status == "Open" and closure != "":
            add_anomaly("closure_date", AnomalyType.LOGICAL_CONTRADICTION, Severity.HIGH, "Open case has a closure_date", closure)
        elif status == "Closed" and closure == "":
            add_anomaly("closure_date", AnomalyType.MISSING_VALUE, Severity.HIGH, "Closed case is missing closure_date", closure)
            
        # Temporal Contradiction (only if BOTH are explicitly canonical, meaning parsed unambiguously as YYYY-MM-DD)
        if intake_canonical and closure_canonical:
            if closure < intake:
                add_anomaly("closure_date", AnomalyType.LOGICAL_CONTRADICTION, Severity.CRITICAL, "closure_date is unambiguously before intake_date", closure, sig=f"intake={intake}")
                
        # Identity Variants and Exact Duplicates
        if case_id != "":
            if exact_case_counts.get(case_id, 0) > 1:
                add_anomaly("case_id", AnomalyType.EXACT_DUPLICATE, Severity.HIGH, f"Exact duplicate case_id found ({exact_case_counts[case_id]} times)", case_id)
            
            id_sig = normalize_string_signature(case_id)
            variants = id_sig_to_raw.get(id_sig, set())
            if len(variants) > 1:
                unique_variants = sorted(list(variants))
                add_anomaly("case_id", AnomalyType.CANDIDATE_IDENTITY_VARIANT, Severity.HIGH, f"Raw value shares normalized signature with: {unique_variants}", case_id, sig=id_sig)
                
        # Category Candidate Variants
        category = row.get("category", "")
        if category != "":
            cat_sig = normalize_string_signature(category)
            variants = cat_sig_to_raw.get(cat_sig, set())
            if len(variants) > 1:
                unique_variants = sorted(list(variants))
                add_anomaly("category", AnomalyType.CANDIDATE_CATEGORY_VARIANT, Severity.LOW, f"Raw value shares normalized signature with: {unique_variants}", category, sig=cat_sig)

    return anomalies

def generate_anomaly_report(anomalies: List[Anomaly]) -> pd.DataFrame:
    records = []
    for a in anomalies:
        records.append({
            "source_row": a.source_row,
            "case_id": a.case_id,
            "field": a.field,
            "anomaly_type": a.anomaly_type.value,
            "severity": a.severity.value,
            "observed_value": a.observed_value,
            "evidence": a.evidence,
            "normalized_signature": a.normalized_signature
        })
    df_report = pd.DataFrame(records)
    if not df_report.empty:
        df_report = df_report.sort_values(by=["source_row", "field", "anomaly_type"]).reset_index(drop=True)
    return df_report
