import json
import os
import sys
from pathlib import Path
import pandas as pd

def load_json(path):
    if not os.path.exists(path):
        print(f"ERROR: Required analytical artifact not found: {path}")
        sys.exit(1)
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"ERROR: Malformed JSON in upstream output: {path}")
            sys.exit(1)

def load_csv(path):
    if not os.path.exists(path):
        print(f"ERROR: Required analytical artifact not found: {path}")
        sys.exit(1)
    return pd.read_csv(path)

def generate_decision_evidence(outputs_dir, analysis_results):
    decision_evidence = []
    
    for q in analysis_results:
        question_id = q.get("question_id")
        
        evidence_entry = {
            "question_id": question_id,
            "question": q.get("original_question", "Unknown"),
            "final_conclusion": q.get("interpretation", "Unknown"),
            "metric": q.get("metric_definition", "Unknown"),
            "confidence": q.get("confidence", "Unknown"),
            "limitations": q.get("limitations", "Unknown"),
            "direct_inputs": ["analysis_results.json"],
            "upstream_provenance": [
                "cleaned_cases.csv",
                "record_quality.csv",
                "cleaning_audit.csv",
                "phase2_anomaly_report.csv",
                "baseline_profile.json",
                "raw/case-export-2023-2025.csv"
            ]
        }
        
        if question_id == "Q1":
            evidence_entry["evidence_fields"] = ["intake_date", "closure_date", "status"]
            evidence_entry["years"] = q.get("results_by_year", {})
            evidence_entry["coverage_metrics"] = {
                y: m.get("coverage") for y, m in q.get("results_by_year", {}).items()
            }
        elif question_id == "Q2":
            evidence_entry["evidence_fields"] = ["district", "category", "intake_date", "closure_date"]
            evidence_entry["primary_driver"] = q.get("driver_evidence", {}).get("primary_driver")
            evidence_entry["closures_lost"] = q.get("driver_evidence", {}).get("closures_lost")
        elif question_id == "Q3":
            evidence_entry["evidence_fields"] = ["priority"]
            evidence_entry["missing_evidence"] = q.get("evidence", {})
            # Update wording exactly as requested
            evidence_entry["final_conclusion"] = "Priority is missing for 100% of 2023 records (4,458/4,458), preventing a pre-2024 high-priority baseline."
            
        decision_evidence.append(evidence_entry)
        
    with open(os.path.join(outputs_dir, "decision_evidence.json"), "w") as f:
        json.dump(decision_evidence, f, indent=2)
        
    with open(os.path.join(outputs_dir, "decision_evidence.md"), "w") as f:
        f.write("# Decision Evidence Report\n\n")
        f.write("## Executive Summary\n")
        f.write("This report provides a verifiable, data-backed summary of the organizational performance trend from 2023-2025. The analysis establishes a clear decline in closure rates, localizes the decline geographically, and confirms that triage priority performance cannot be evaluated due to missing baseline data.\n\n")
        
        f.write("## Data Quality Context\n")
        f.write("- The raw source data contains significant missing fields (notably priority) and temporal contradictions.\n")
        f.write("- Our methodology strictly excludes invalid or unobservable records rather than guessing or fabricating timelines.\n")
        f.write("- The data supports trend analysis and localization, but does not contain fields that could prove causality.\n\n")
        
        for e in decision_evidence:
            f.write(f"## {e['question_id']}\n\n")
            f.write(f"### Question\n{e['question']}\n\n")
            
            if e['confidence'] == "NOT ANSWERABLE":
                f.write(f"### Answer\nNOT ANSWERABLE\n\n")
                f.write(f"### Why\n{e['final_conclusion']}\n\n")
                f.write(f"### Evidence\n")
                missing = e.get("missing_evidence", {})
                for k, v in missing.items():
                    f.write(f"- {k}: {v}\n")
                f.write("\n")
                f.write(f"### Additional Data Required\nA retrospective classification of 2023 cases into priority bands to establish the pre-2024 baseline.\n\n")
            else:
                f.write(f"### Metric\n{e['metric']}\n\n")
                f.write(f"### Result\n{e['final_conclusion']}\n\n")
                f.write(f"### Evidence\n")
                if "years" in e:
                    for y, m in e["years"].items():
                        f.write(f"- {y}: Rate {m['rate']:.1%}, Denom: {m['denominator']}\n")
                if "primary_driver" in e:
                    f.write(f"- Primary Driver: {e['primary_driver']}\n")
                    f.write(f"- Closures Lost: {e['closures_lost']}\n")
                f.write("\n")
                
                f.write(f"### Coverage\n")
                if "coverage_metrics" in e:
                    for y, cov in e["coverage_metrics"].items():
                        f.write(f"- {y}: {cov:.1%}\n")
                f.write("\n")
                
                f.write(f"### Confidence\n{e['confidence']}\n\n")
                f.write(f"### Limitations\n{e['limitations']}\n\n")
                
        f.write("## What the Data Can Support\n")
        f.write("- Systemic changes in resolution speed across the organization.\n")
        f.write("- Geographic or category-based localization of deteriorating performance.\n\n")
        f.write("## What the Data Cannot Support\n")
        f.write("- Causal explanations for the deterioration (e.g., *why* Weybridge dropped in performance).\n")
        f.write("- Efficacy of the 2024 triage process, due to the absolute lack of 2023 baseline priority data.\n")

def generate_data_quality_summary(outputs_dir, baseline_profile, rq):
    dq = {
        "raw_row_count": baseline_profile["general"]["total_rows"],
        "raw_column_count": baseline_profile["general"]["total_columns"],
        "duplicate_case_ids": baseline_profile["identifiers"]["case_id"]["exact_duplicate_count"],
        "exact_duplicate_rows": 28, # Physically removed rows
        "missing_priority_overall": baseline_profile["categorical"]["priority"]["missing_count"],
        "missing_closure_dates": baseline_profile["dates"]["closure_date"]["missing_count"],
        "retained_rows": len(rq),
        "excluded_from_duration_analysis": len(rq[~rq["eligible_for_duration_analysis"]]),
        "source_pipeline": ["baseline_profile.json", "record_quality.csv"]
    }
    
    with open(os.path.join(outputs_dir, "data_quality_summary.json"), "w") as f:
        json.dump(dq, f, indent=2)
        
    with open(os.path.join(outputs_dir, "data_quality_summary.md"), "w") as f:
        f.write("# Data Quality Summary\n\n")
        f.write(f"- **Raw row count**: {dq['raw_row_count']}\n")
        f.write(f"- **Raw column count**: {dq['raw_column_count']}\n")
        f.write(f"- **Duplicate case IDs**: {dq['duplicate_case_ids']}\n")
        f.write(f"- **Exact duplicate rows removed**: {dq['exact_duplicate_rows']}\n")
        
        pct_missing = (dq['missing_priority_overall'] / dq['raw_row_count']) * 100
        f.write(f"- **Missing priority**: Priority is missing for {dq['missing_priority_overall']} of {dq['raw_row_count']} records ({pct_missing:.2f}%) overall.\n")
        
        f.write(f"- **Missing closure dates**: {dq['missing_closure_dates']}\n")
        f.write(f"- **Retained rows**: {dq['retained_rows']}\n")
        f.write(f"- **Excluded from duration analysis**: {dq['excluded_from_duration_analysis']}\n")

def generate_cleaning_summary(outputs_dir, cleaning_audit):
    # Group by rule_id and aggregate counts
    rule_counts = cleaning_audit["rule_id"].value_counts().to_dict()
    
    summary = {
        "auto_repairs": len(cleaning_audit[cleaning_audit["action"] == "repair"]),
        "retained_with_flag": len(cleaning_audit[cleaning_audit["action"] == "flag"]),
        "physically_dropped": 28, # Known constant from Phase 3 deduplication
        "rules_applied": rule_counts
    }
    
    with open(os.path.join(outputs_dir, "cleaning_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
        
    with open(os.path.join(outputs_dir, "cleaning_summary.md"), "w") as f:
        f.write("# Cleaning Summary\n\n")
        f.write("This summarizes the remediation actions taken during Phase 3.\n\n")
        f.write(f"- **Auto-repairs applied**: {summary['auto_repairs']}\n")
        f.write(f"- **Records retained with flags**: {summary['retained_with_flag']}\n")
        f.write(f"- **Records physically dropped (exact duplicates)**: {summary['physically_dropped']}\n\n")
        
        f.write("## Rules Applied\n")
        for rule_id, count in summary['rules_applied'].items():
            f.write(f"- **{rule_id}**: {count} affected records\n")

def generate_confidence_summary(outputs_dir):
    confidence = {
        "Q1": {
            "description": "Descriptive confidence in observed trend.",
            "confidence": "HIGH",
            "reasoning": "Mathematical consistency across multiple metrics (30-day rate, median duration). Methodological rigor in addressing right-censorship."
        },
        "Q2": {
            "description": "Confidence in localization of the observed deterioration.",
            "confidence": "HIGH",
            "reasoning": "The analysis localizes the deterioration to Weybridge and shows that the pattern persists across major categories, but the available data does not establish a causal mechanism."
        },
        "Q3": {
            "description": "Efficacy of 2024 triage process.",
            "confidence": "NOT ANSWERABLE",
            "reasoning": "Total lack of baseline data for the pre-triage period (100% missing priority in 2023)."
        }
    }
    
    with open(os.path.join(outputs_dir, "confidence_summary.json"), "w") as f:
        json.dump(confidence, f, indent=2)

def main():
    if len(sys.argv) > 1:
        outputs_dir = Path(sys.argv[1]).resolve()
    else:
        outputs_dir = Path(os.path.join(os.path.dirname(__file__), "..", "..", "outputs")).resolve()
    
    # 1. Verify existence of required upstream artifacts
    analysis_results = load_json(outputs_dir / "analysis_results.json")
    baseline_profile = load_json(outputs_dir / "baseline_profile.json")
    
    rq = load_csv(outputs_dir / "record_quality.csv")
    cleaned_cases = load_csv(outputs_dir / "cleaned_cases.csv")
    cleaning_audit = load_csv(outputs_dir / "cleaning_audit.csv")
    
    # 2. Check Reconciliation
    raw_rows = baseline_profile["general"]["total_rows"]
    retained_rows = len(rq)
    dropped_rows = 28
    
    if raw_rows != retained_rows + dropped_rows:
        print(f"ERROR: Reconciliation failed! Raw ({raw_rows}) != Retained ({retained_rows}) + Dropped ({dropped_rows})")
        sys.exit(1)
        
    q3_evidence = analysis_results[2].get("evidence", {})
    if q3_evidence.get("2023_total_cases") != q3_evidence.get("2023_missing_priority") + q3_evidence.get("observable_2023_high_priority_cases"):
        print("ERROR: Q3 reconciliation failed!")
        sys.exit(1)
        
    # 3. Generate Reports
    generate_decision_evidence(outputs_dir, analysis_results)
    generate_data_quality_summary(outputs_dir, baseline_profile, rq)
    generate_cleaning_summary(outputs_dir, cleaning_audit)
    generate_confidence_summary(outputs_dir)
    
    print("Successfully generated deterministic evidence reports.")

if __name__ == "__main__":
    main()
