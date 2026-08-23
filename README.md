# Brite Hackathon — Dirty Data, Real Decisions

## 1. Quick Start

### Clone

```bash
git clone https://github.com/teja0604/Brite.git
cd Brite
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:PYTHONPATH="src"
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
export PYTHONPATH=src
```

## 2. Run Tests

### Windows:
```powershell
$env:PYTHONPATH="src"; python -m pytest -v
```

### Linux/macOS:
```bash
PYTHONPATH=src python -m pytest -v
```

The test suite covers edge-case data scenarios, deterministic ingestion rules, identity mapping permutations, reconciliation logic, and corruption matrix adversarial testing.

Expected result: all tests pass.

## 3. Complete Surprise Challenge Execution

The pipeline requires specific raw inputs provided by the organizer to execute.

The original input is expected at:
`data/raw/case-export-2023-2025.csv`

The supplementary Surprise Challenge input is expected at:
`data/raw/2 - Dirty Data, Real Decisions/case-export-supplementary.csv`

Both files are included in this repository to ensure a fresh clone can immediately reproduce the entire pipeline without requiring manual data placement. Do not modify the CSV contents.

The pipeline executes in two explicit stages.

First, generate the frozen upstream artifacts (S2-S5):

### Windows:
```powershell
$env:PYTHONPATH="src"; python -m dirty_data.freeze_artifacts
```
### Linux/macOS:
```bash
PYTHONPATH=src python -m dirty_data.freeze_artifacts
```

Second, run the official S6 release which consumes the frozen artifacts, performs analytics, and executes independent verification:

### Windows:
```powershell
$env:PYTHONPATH="src"; python run_s6_release.py
```
### Linux/macOS:
```bash
PYTHONPATH=src python run_s6_release.py
```

Success is confirmed when the script outputs `S6 release verification passed` and verification artifacts are generated.

## 4. What the Project Does

This project is a strictly reproducible Python data pipeline. It does not use a web application, dashboard, or database.

It processes the dirty data through explicit, auditable stages:
Raw data → deterministic ingestion → profiling → anomaly detection → auditable remediation → analytical analysis → supplementary identity matching → field-level comparison → reconciliation → frozen evidence → S6 analytics → independent verification.

Every data-quality decision and reconciliation rule is explicitly recorded, preserving all evidence and retaining deterministic traceability.

## 5. Technology Stack

| Technology | Why it is used |
|---|---|
| Python | Reproducible data processing and analytical logic |
| pandas | Tabular CSV processing |
| pytest | Regression, edge-case, adversarial, and verification testing |
| numpy | Numerical calculations via pandas |
| CSV/JSON | Transparent and portable data/evidence artifacts |
| Git | Versioned engineering history |

A database, API, frontend, or heavy data-engineering framework was not required because the challenge focuses on auditable CSV cleaning, deterministic analytical methodology, and reproducible calculations rather than interactive user serving or distributed scaling.

## 6. Input Data

**Original:**
`data/raw/case-export-2023-2025.csv`
This is the baseline raw dataset containing case records, dates, and priorities.

**Supplementary:**
`data/raw/2 - Dirty Data, Real Decisions/case-export-supplementary.csv`
This is the operational update provided during the Surprise Challenge.

Both files are **organizer-provided raw inputs**. They are never overwritten. All transformations result in generated outputs inside the `outputs/` directory.

## 7. Important Outputs

These are the core outputs genuinely produced by the pipeline in the `outputs/` directory.

### Baseline / Cleaning
- **s2_original_canonical.json**: The baseline cleaned dataset adhering to a strict canonical schema without silent date assumptions.
- **s2_supplementary_canonical.json**: The canonicalized supplementary dataset.

### Evidence / Reporting
- **s3_aligned.json**: The physical matched identity ledger preserving all raw duplicate records.
- **s3_identity_index.json**: The cardinality classifications (`MANY_TO_ONE`, `SUPPLEMENTARY_ONLY`, etc.).
- **s4_comparison.json**: Record-by-record deterministic field comparisons (`CONFLICT`, `MISSING_ONE_SIDE`, etc.).
- **s5_audit.json**: The exact cleaning and reconciliation decision log for every modified or imputed value.

### Surprise Challenge / S6
- **outputs/frozen/**: The immutable collection of S2-S5 JSON artifacts used as evidence for S6.
- **outputs/s6_population_disposition.csv**: Tracks exactly how every input row was handled (e.g., `PRIMARY_CASE`, `EXCLUDED_WITH_REASON`).
- **outputs/s6/observations.csv**: The final, reconciled population eligible for analysis, containing explicit origin provenance.
- **outputs/s6/exclusions.csv**: Records rejected from analysis due to logical errors or date contradictions.
- **outputs/s6/q1.csv**, **q2.csv**, **q3.csv**: The final answers to the organizer's analytical questions.
- **outputs/s6/supplementary_only.csv**: Separately evaluated records that only existed in the supplementary source.
- **outputs/s6/many_to_one_physical.csv**: Separately evaluated multi-record identities.
- **outputs/s6/verification.json**: The independent verifier's mathematical audit results.

## 8. Surprise Challenge Flow

```text
Original CSV
     +
Supplementary CSV
     ↓
Canonical representation
     ↓
Identity matching
     ↓
Field comparison
     ↓
Reconciliation
     ↓
Frozen evidence
     ↓
S6 analytics
     ↓
Independent verification
```

The system performs **explicit identity matching** to map records without immediately destroying them. It then performs **field-level reconciliation** with **documented conflict precedence** (e.g., Supplementary wins on closure dates, Original wins on business categories). 

Every value retains exact source-row **provenance**. **MANY_TO_ONE handling** preserves Original physical records without creating **synthetic durations**, and the **supplementary-only population** is maintained and analyzed independently. Data lacking sufficient evidence triggers **explicit exclusions**.

## 9. Analytical Questions

### Question 1
**Have case closure times increased between 2023 and 2025, and if so, by how much?**

### Question 2
**If closure times have changed, what is driving the change?**

### Question 3
**Did the case triage process introduced during 2024 reduce closure times for high-priority cases?**

The pipeline calculates the supported answers with explicit denominators, eligibility rules, and confidence levels. Unsupported assumptions are explicitly flagged as unanswerable.

## 10. Data Safety and Auditability

- Raw data is not overwritten.
- Transformations produce derived outputs.
- Ambiguous dates are not silently guessed.
- Identity variants are not silently merged.
- Cleaning decisions are logged.
- Source-row provenance is preserved.
- Reconciliation decisions are explicit.
- Analytical outputs are independently verified.

## 11. Independent Verification

### Windows:
```powershell
$env:PYTHONPATH="src"; python run_s6_release.py
```
### Linux/macOS:
```bash
PYTHONPATH=src python run_s6_release.py
```

The project contains independent verification logic that checks final analytical artifacts against upstream evidence. This process reads directly from the frozen JSON evidence, bypassing the S6 analytics logic entirely. It includes adversarial corruption testing to detect tampered or mathematically inconsistent analytical outputs, ensuring results aren't simply echoing a flawed calculation.

## 12. Reproducibility Checklist

1. Clone repository.
2. Install dependencies.
3. (Optional) Verify raw inputs are present in `data/raw`.
4. Set PYTHONPATH=src.
5. Run the complete test suite.
6. Generate required frozen evidence.
7. Run the official release runner.
8. Confirm verification succeeds.
9. Review final outputs.

## 13. Repository Structure

```text
Brite/
├── data/
│   └── raw/
├── organizer/
├── src/
│   └── dirty_data/
├── tests/
├── outputs/
├── requirements.txt
├── run_s6_release.py
├── DECISIONS.md
├── AI-USAGE.md
└── README.md
```

## 14. Troubleshooting

### Python module not found

**Windows:**
```powershell
$env:PYTHONPATH="src"
```
**Linux/macOS:**
```bash
export PYTHONPATH=src
```

### Missing supplementary input
Ensure you have not deleted the repository's provided supplementary file at:
`data/raw/2 - Dirty Data, Real Decisions/case-export-supplementary.csv`

### Missing frozen artifacts
Generate the upstream artifacts before running analytics:
```powershell
$env:PYTHONPATH="src"; python -m dirty_data.freeze_artifacts
```

### Tests fail
```powershell
$env:PYTHONPATH="src"; python -m pytest -v
```
Do not bypass failing tests; they enforce data safety constraints.

## 15. Judge / Evaluation Quick Path

### Windows
```powershell
# 1. Clone
git clone https://github.com/teja0604/Brite.git
cd Brite

# 2. Create environment & 3. Install requirements
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. (Optional) Verify organizer inputs
# Verify case-export-supplementary.csv is in data/raw/2 - Dirty Data, Real Decisions/

# 5. Set PYTHONPATH
$env:PYTHONPATH="src"

# 6. Run pytest
python -m pytest -v

# 7. Generate frozen artifacts
python -m dirty_data.freeze_artifacts

# 8. Run official S6 release & 9. Confirm verification
python run_s6_release.py

# 10. Review final outputs in outputs/s6/
```

### Linux/macOS
```bash
# 1. Clone
git clone https://github.com/teja0604/Brite.git
cd Brite

# 2. Create environment & 3. Install requirements
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. (Optional) Verify organizer inputs
# Verify case-export-supplementary.csv is in data/raw/2 - Dirty Data, Real Decisions/

# 5. Set PYTHONPATH
export PYTHONPATH=src

# 6. Run pytest
python -m pytest -v

# 7. Generate frozen artifacts
python -m dirty_data.freeze_artifacts

# 8. Run official S6 release & 9. Confirm verification
python run_s6_release.py

# 10. Review final outputs in outputs/s6/
```
