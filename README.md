# Brite Hackathon — Dirty Data, Real Decisions

This is a deterministic Python data-quality, reconciliation, and analytics pipeline. It processes the organizer's original dirty dataset alongside the Surprise Challenge supplementary dataset. The pipeline preserves raw evidence and provenance by never modifying source files, explicitly resolving identities, isolating exclusions, and producing independently verified analytical results.

## Judge Quick Start

**1. Clone the repository and enter the directory:**
```bash
git clone https://github.com/teja0604/Brite.git
cd Brite
```

**2. Create and activate a virtual environment:**

*Windows PowerShell:*
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*Linux/macOS:*
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies:**
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**4. Run the clean-clone test suite:**

*Windows PowerShell:*
```powershell
$env:PYTHONPATH="src"
python -m pytest -v
```

*Linux/macOS:*
```bash
export PYTHONPATH=src
python -m pytest -v
```

*(Expected result: `113 passed`)*

**5. Run the production pipeline:**
*(This requires the same `$env:PYTHONPATH="src"` or `export PYTHONPATH=src` environment variable set in step 4).*

```bash
python -m dirty_data.freeze_artifacts
python run_s6_release.py
```

*(Expected result: `S6 release verification passed`)*

**6. Run the post-production test suite:**
```bash
python -m pytest -v
```

*(Expected result: `113 passed`)*

## Requirements

The verified environment requires:
- **Python**: Python 3.10+ recommended (Python 3.12 has been verified)
- **Dependencies**: Come strictly from `requirements.txt` (`pandas`, `pytest`, `numpy`)

## Raw Datasets

Raw datasets are immutable inputs and must not be modified.

The solution expects the organizer-provided CSV files at these exact paths:

Expected repository layout:

```text
data/
└── raw/
    ├── case-export-2023-2025.csv
    └── 2 - Dirty Data, Real Decisions/
        ├── case-export-supplementary.csv
        └── READ ME FIRST.md
```

If you are using the organizer-provided ZIP files, extract the datasets and place the corresponding CSV files at the exact paths above. Use the files exactly as provided by the organizer; do not rename, modify, clean, or preprocess them.

For confirmation, after extracting the ZIP files, you can verify that the files exist at these locations before running the commands in **Judge Quick Start**.

The current repository already contains these required raw CSV files, so a normal fresh clone does not require any additional data placement.

## Outputs

The clean-clone test suite is designed to run without pre-generated `outputs/`. When the production pipeline is executed, it generates the following output locations:

`outputs/frozen/`

`outputs/s6/q1.csv`
`outputs/s6/q2.csv`
`outputs/s6/q3.csv`
`outputs/s6/observations.csv`
`outputs/s6/exclusions.csv`
`outputs/s6/supplementary_only.csv`
`outputs/s6/many_to_one_physical.csv`
`outputs/s6/verification.json`

`outputs/s6_population_disposition.csv`

## Answers to Q1, Q2, and Q3

The three primary evaluator-facing answer files are:

- **Q1** → `outputs/s6/q1.csv`
- **Q2** → `outputs/s6/q2.csv`
- **Q3** → `outputs/s6/q3.csv`

### Q1 — Closure Performance Over Time

Measures the 30-day closure rate and median closure duration for the primary reconciled population.

**Result:** The 30-day closure rate decreased from **44.35% in 2023** to **38.57% in 2025**, while median closure duration increased from **34 days** to **38 days**. This indicates worsening closure performance over the period covered by the data.

Evidence: `outputs/s6/q1.csv`

### Q2 — Drivers of Closure Performance

Breaks down the same closure metrics by **district and case category** to identify where closure performance differs.

**Result:** Performance varies substantially across districts and categories. For example, median closure duration ranges from **30 days in Ash Hill** to **48 days in Weybridge**. By category, **Expedited** cases have a median of **14 days**, while **Complex** cases have a median of **73 days**.

These are observed differences in the reconciled data; the pipeline does not claim that these factors independently cause the differences.

Evidence: `outputs/s6/q2.csv`

### Q3 — Priority Triage Analysis

Evaluates the priority-triage metrics for the years supported by the reconciled evidence.

**Result:** From 2024 to 2025, the 30-day closure rate decreased from **41.63% to 37.30%**, while median closure duration increased from **35 days to 38.5 days**.

A 2023 priority baseline is **not reported**, because the required 2023 priority evidence is unavailable. The pipeline therefore does not fabricate a 2023 comparison.

Evidence: `outputs/s6/q3.csv`

## Independent Verification

The pipeline leverages an isolated independent verifier (`s6_independent_verifier.py`). The independent verifier recalculates required metrics from frozen upstream evidence independently of the production analytics implementation and compares the results against production outputs. If any production output differs from the upstream evidence, the release fails.

## Troubleshooting

- **Python not found**: Ensure Python 3.10+ is installed and available in your system's PATH.
- **PowerShell activation fails**: On Windows PowerShell, you may need to run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted` before activating the environment.
- **Missing `requirements.txt`**: Ensure you are executing commands from the repository root (`Brite/`), not the parent directory.
- **`ModuleNotFoundError` for `dirty_data`**: You must set your PYTHONPATH appropriately for your OS (e.g., `$env:PYTHONPATH="src"` on Windows or `export PYTHONPATH=src` on Linux/macOS).
- **Missing frozen artifacts**: Run `python -m dirty_data.freeze_artifacts` before `python run_s6_release.py`.
- **Disk/temp-space problems**: The test suite generates dynamic isolated environments. If you encounter disk space errors on your primary drive during testing, run pytest with a custom base temp directory (e.g., `python -m pytest -v --basetemp=D:\pytest_temp`).
