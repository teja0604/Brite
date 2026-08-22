import json
import os
import shutil
import hashlib
from pathlib import Path
import pytest
import subprocess

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
BUILD_SCRIPT = Path(__file__).resolve().parent.parent / "src" / "dirty_data" / "build_reports.py"
RAW_FILE = Path(__file__).resolve().parent.parent / "data" / "raw" / "case-export-2023-2025.csv"

def get_json(filename):
    with open(OUTPUTS_DIR / filename, "r") as f:
        return json.load(f)

def sha256_file(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def test_summary_row_counts():
    dq = get_json("data_quality_summary.json")
    assert dq["raw_row_count"] == 15100, "1. Summary contains expected raw row count."
    assert dq["retained_rows"] == 15072, "2. Summary contains expected retained row count."
    assert dq["missing_priority_overall"] == 5856
    
def test_missing_priority_wording():
    # Read the markdown summaries to check wording
    with open(OUTPUTS_DIR / "decision_evidence.md", "r") as f:
        de_md = f.read()
    
    assert "Priority is missing for 100% of 2023 records (4,458/4,458), preventing a pre-2024 high-priority baseline." in de_md
    
    with open(OUTPUTS_DIR / "data_quality_summary.md", "r") as f:
        dq_md = f.read()
    
    assert "Priority is missing for 5856 of 15100 records (38.78%) overall." in dq_md

def test_cleaning_summary():
    cs = get_json("cleaning_summary.json")
    assert cs["physically_dropped"] == 28, "3. Cleaning summary reconciles dropped rows."

def test_q1_evidence():
    de = get_json("decision_evidence.json")
    q1 = next(q for q in de if q["question_id"] == "Q1")
    assert "30-day closure rate" in q1["metric"], "4. Q1 evidence references the correct metric."
    assert q1["years"]["2023"]["denominator"] == 3986, "5. Q1 denominator is preserved."
    assert q1["years"]["2025"]["not_observable_population"] == 348, "6. Q1 not-observable count is preserved."
    # Regression checks against known organizer dataset
    assert abs(q1["years"]["2023"]["rate"] - 0.44455) < 0.0001
    assert abs(q1["years"]["2025"]["rate"] - 0.34440) < 0.0001

def test_q2_evidence():
    de = get_json("decision_evidence.json")
    q2 = next(q for q in de if q["question_id"] == "Q2")
    assert "district" in q2["evidence_fields"], "7. Q2 preserves district evidence."
    assert "category" in q2["evidence_fields"], "8. Q2 preserves category/composition evidence."
    
    # 9. Q2 does not make causal claims
    assert "causal mechanism" in q2["final_conclusion"].lower()
    assert "localizes" in q2["final_conclusion"].lower()
    assert "largest observed contributor" in q2["final_conclusion"].lower()

def test_q3_evidence():
    de = get_json("decision_evidence.json")
    q3 = next(q for q in de if q["question_id"] == "Q3")
    assert q3["confidence"] == "NOT ANSWERABLE", "10. Q3 remains NOT ANSWERABLE."
    assert q3["missing_evidence"]["2023_missing_priority"] == 4458, "11. Q3 contains the missing-priority evidence."

def test_no_absolute_paths():
    for file in ["decision_evidence.json", "decision_evidence.md", "data_quality_summary.json", "data_quality_summary.md", "cleaning_summary.json", "cleaning_summary.md", "confidence_summary.json"]:
        with open(OUTPUTS_DIR / file, "r") as f:
            content = f.read()
            assert "C:\\" not in content, "13. No absolute local paths appear."
            assert "d:\\" not in content.lower(), "13. No absolute local paths appear."

def test_raw_file_integrity():
    assert RAW_FILE.exists(), "Raw file must exist."
    # We use SHA-256 for cryptographic integrity checking of the organizer's raw file
    actual_hash = sha256_file(RAW_FILE)
    # This hash represents the immutable organizer-provided source for this challenge.
    expected_hash = "f65bec452b2f25404fc7b41d7d9c1ed35ef993fded974cf432cb36945ac27dd6"
    assert actual_hash == expected_hash, f"Raw file integrity failed! Hash is {actual_hash}"
    
def test_raw_file_integrity_detects_change(tmp_path):
    # Test that the integrity check actually works when a file is modified (using a temp file)
    test_file = tmp_path / "fake-raw.csv"
    test_file.write_text("modified,data")
    assert sha256_file(test_file) != "f65bec452b2f25404fc7b41d7d9c1ed35ef993fded974cf432cb36945ac27dd6"

def test_failure_handling(tmp_path):
    script = BUILD_SCRIPT.read_text().replace('outputs_dir = Path(os.path.join(os.path.dirname(__file__), "..", "..", "outputs")).resolve()', f'outputs_dir = Path("{str(tmp_path).replace("\\", "\\\\")}")')
    temp_script = tmp_path / "temp_build.py"
    temp_script.write_text(script)
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent / "src")
    result = subprocess.run(["python", str(temp_script)], capture_output=True, text=True, env=env)
    
    assert result.returncode == 1
    assert "ERROR: Required analytical artifact not found" in result.stdout
    
    (tmp_path / "analysis_results.json").write_text("{malformed")
    result = subprocess.run(["python", str(temp_script)], capture_output=True, text=True, env=env)
    assert result.returncode == 1
    assert "ERROR: Malformed JSON in upstream output" in result.stdout

def test_determinism():
    def get_all_hashes():
        hashes = {}
        for file in ["decision_evidence.json", "decision_evidence.md", "data_quality_summary.json", "data_quality_summary.md", "cleaning_summary.json", "cleaning_summary.md", "confidence_summary.json"]:
            hashes[file] = sha256_file(OUTPUTS_DIR / file)
        return hashes
        
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent / "src")
    
    subprocess.run(["python", str(BUILD_SCRIPT)], capture_output=True, text=True, env=env)
    run1 = get_all_hashes()
    
    subprocess.run(["python", str(BUILD_SCRIPT)], capture_output=True, text=True, env=env)
    run2 = get_all_hashes()
    
    for k in run1:
        assert run1[k] == run2[k], f"File {k} is not deterministic"
