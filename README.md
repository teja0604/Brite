# Brite Hackathon — Dirty Data, Real Decisions

## 1. What this project does

This is a deterministic Python data-quality, reconciliation, and analytics pipeline. It processes the organizer's original dirty dataset alongside the Surprise Challenge supplementary dataset. The pipeline preserves raw evidence and provenance by never modifying source files. It systematically performs identity matching, field-level comparison, explicit reconciliation, analytics, and independent verification. It produces defensible answers to the organizer's three questions through dedicated Q1, Q2, and Q3 outputs.

## 2. Requirements

Python: Python 3.8+ (or compatible 3.x)
Git: required
Operating Systems: Windows, Linux, macOS
Database: not required
Frontend: not required
Node.js: not required
Dependencies: `pandas`, `pytest`, `numpy` (as specified in `requirements.txt`)

## 3. Clone the repository

Windows PowerShell:
```powershell
git clone https://github.com/teja0604/Brite.git
cd Brite
```

Linux/macOS:
```bash
git clone https://github.com/teja0604/Brite.git
cd Brite
```

## 4. Create Python environment and install dependencies

Windows PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Verify organizer input data

The required raw files for the complete pipeline, including the Surprise Challenge, are:
- `data/raw/case-export-2023-2025.csv`
- `data/raw/2 - Dirty Data, Real Decisions/case-export-supplementary.csv`

These are organizer-provided raw inputs and must not be manually edited. The supplementary CSV is now committed to the repository, meaning a fresh clone will already contain it, allowing the pipeline to execute immediately.

## 6. Set PYTHONPATH

Windows PowerShell:
```powershell
$env:PYTHONPATH="src"
```

Linux/macOS:
```bash
export PYTHONPATH=src
```
This allows the `dirty_data` package to be imported correctly from the `src/` directory.

## 7. Run the complete test suite FIRST

Windows PowerShell:
```powershell
$env:PYTHONPATH="src"; python -m pytest -v
```

Linux/macOS:
```bash
PYTHONPATH=src python -m pytest -v
```

The 127 tests cover edge-case data scenarios, deterministic ingestion rules, identity mapping permutations, reconciliation logic, and corruption matrix adversarial testing. 

**Expected result**: all tests pass. If tests fail, stop and investigate instead of ignoring the failure.

## 8. Run the complete production pipeline

The pipeline must be executed in two distinct stages.

First, generate the frozen upstream artifacts (S2-S5):

Windows PowerShell:
```powershell
$env:PYTHONPATH="src"; python -m dirty_data.freeze_artifacts
```

Linux/macOS:
```bash
PYTHONPATH=src python -m dirty_data.freeze_artifacts
```

Second, run the official S6 release which consumes the frozen artifacts, performs analytics, and executes independent verification:

Windows PowerShell:
```powershell
$env:PYTHONPATH="src"; python run_s6_release.py
```

Linux/macOS:
```bash
PYTHONPATH=src python run_s6_release.py
```

## 9. What successful execution looks like

Successful execution outputs `S6 release verification passed` to the console. This indicates that:
- Tests have passed (if run previously)
- Frozen JSON artifacts were successfully generated from the raw data
- S6 analytics completed its calculations
- The independent mathematical verifier passed
- Corruption/tamper verification passed perfectly
- The final release runner exited without errors

## 10. Where the outputs are stored

### Final analytical outputs
- `outputs/s6/q1.csv`: Answer and evidence for Question 1 (Closure Times)
- `outputs/s6/q2.csv`: Answer and evidence for Question 2 (Drivers of Change)
- `outputs/s6/q3.csv`: Answer and evidence for Question 3 (Triage Process)

### Supporting outputs
- `outputs/s6/observations.csv`: The primary reconciled dataset eligible for analysis
- `outputs/s6/exclusions.csv`: Records rejected from analysis due to logical errors
- `outputs/s6/supplementary_only.csv`: Records existing only in the supplementary dataset
- `outputs/s6/many_to_one_physical.csv`: Resolved multi-record identities
- `outputs/s6/verification.json`: Independent verifier's mathematical audit results
- `outputs/s6_population_disposition.csv`: Tracking for how every record was handled

### Frozen evidence
- `outputs/frozen/`: Immutable collection of S2-S5 JSON artifacts (e.g., `s2_original_canonical.json`, `s5_audit.json`) used as evidence for S6.

## 11. How to inspect the final answers

Windows PowerShell:
```powershell
Import-Csv outputs\s6\q1.csv | Format-Table
Import-Csv outputs\s6\q2.csv | Format-Table
Import-Csv outputs\s6\q3.csv | Format-Table
```

Linux/macOS:
```bash
cat outputs/s6/q1.csv | column -t -s,
cat outputs/s6/q2.csv | column -t -s,
cat outputs/s6/q3.csv | column -t -s,
```
- `q1.csv` = Question 1
- `q2.csv` = Question 2
- `q3.csv` = Question 3

## 12. Architecture / execution flow

```text
Original raw CSV
        +
Supplementary raw CSV
        ↓
Canonical ingestion
        ↓
Identity matching
        ↓
Field-level comparison
        ↓
Reconciliation
        ↓
Frozen evidence
        ↓
S6 analytics
        ↓
Independent verification
        ↓
Final Q1 / Q2 / Q3 outputs
```

## 13. Surprise Challenge handling

The supplementary operational data is ingested separately without modifying the original baseline. Identities are matched explicitly, and field-level conflicts are reconciled using documented precedence policies (e.g., Supplementary wins on closure dates). Source-row provenance is preserved for all fields. `MANY_TO_ONE` cases are handled according to frozen policy to avoid generating synthetic records, and supplementary-only records are retained independently. Final analytics operate on this rigorously documented population.

## 14. Data safety and auditability

- Raw inputs are not modified.
- Ambiguous dates are not silently guessed.
- Identity variants are not blindly merged.
- Reconciliation decisions are traceable.
- Source-row provenance is preserved.
- Analytical exclusions are explicit.
- Final results are independently verified.
- Outputs are deterministic.

## 15. Judge Quick Start

**Windows PowerShell:**
```powershell
git clone https://github.com/teja0604/Brite.git
cd Brite
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:PYTHONPATH="src"
python -m pytest -v
python -m dirty_data.freeze_artifacts
python run_s6_release.py

# Inspect Outputs
Get-Content outputs\s6\q1.csv
Get-Content outputs\s6\q2.csv
Get-Content outputs\s6\q3.csv
```

**Linux/macOS:**
```bash
git clone https://github.com/teja0604/Brite.git
cd Brite
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
export PYTHONPATH=src
python -m pytest -v
python -m dirty_data.freeze_artifacts
python run_s6_release.py

# Inspect Outputs
cat outputs/s6/q1.csv
cat outputs/s6/q2.csv
cat outputs/s6/q3.csv
```

## 16. Troubleshooting

- **Python not found**: Ensure Python 3.8+ is installed and available in your system's PATH.
- **Virtual environment activation fails**: On Windows, you may need to run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted`.
- **Missing dependency**: Verify that your virtual environment is active before running `pip install -r requirements.txt`.
- **ModuleNotFoundError for 'dirty_data'**: You must set your PYTHONPATH appropriately (e.g. `$env:PYTHONPATH="src"`).
- **Missing frozen artifacts**: Run `python -m dirty_data.freeze_artifacts` before `run_s6_release.py`.
- **Test failure**: Do not bypass test failures; they enforce critical data safety. Verify that the raw inputs haven't been modified.

## 17. Repository structure

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

## 18. Technology stack

- **Python** — deterministic data-processing and analytics pipeline.
- **pandas** — CSV/tabular processing.
- **pytest** — automated regression and adversarial testing.
- **Git** — reproducible version history.

## 19. Why no frontend/database/API

The organizer challenge is fundamentally a reproducible data-processing and analytical task involving static CSV datasets. A deterministic Python CLI pipeline is entirely sufficient for providing auditable results and avoids unnecessary deployment complexity or heavyweight infrastructure.

## 20. Final evaluator checklist

- [ ] Repository cloned
- [ ] Python environment created
- [ ] Dependencies installed
- [ ] Raw organizer inputs present
- [ ] Tests pass
- [ ] Frozen artifacts generated
- [ ] S6 release passes
- [ ] Independent verification passes
- [ ] Q1/Q2/Q3 outputs generated
- [ ] Final outputs available under `outputs/s6/`
