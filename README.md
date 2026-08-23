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

The solution uses the organizer‑provided raw CSV files as immutable inputs. They are already tracked in the repository, so a fresh clone contains them.

Expected repository layout:

```text
data/
└── raw/
    ├── case-export-2023-2025.csv
    └── 2 - Dirty Data, Real Decisions/
        ├── case-export-supplementary.csv
        └── READ ME FIRST.md
```

The raw CSV files must remain unchanged and retain their original filenames. No cleaning, preprocessing, or manual modification should be performed.

The judge does not need to add or move any files; they are present after cloning.

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

**Q1**: Measures the 30-day closure rate and median closure duration, including overall and year-level analysis.

**Q2**: Provides breakdowns of closure performance by the supported dimensions (district and category), using the actual generated `q2.csv` structure (e.g., segmenting by 'Ash Hill', 'Standard', 'Complex', etc.).

**Q3**: Evaluates the priority-triage analysis supported by the reconciled evidence, specifically for 2024 and 2025. The pipeline does NOT fabricate a 2023 baseline where required 2023 priority evidence is unavailable.

## Surprise Challenge Handling

The Surprise Challenge supplementary dataset is ingested separately. Identities are explicitly reconciled, and source evidence/provenance is fully preserved. Conflicts follow documented field-level reconciliation policies. For example, if closure dates are conflicting and the rules indicate a supplementary precedence, that specific field takes precedence, while other fields follow their own documented policies.

## Independent Verification

The pipeline leverages an isolated independent verifier (`s6_independent_verifier.py`). The independent verifier recalculates required metrics from frozen upstream evidence independently of the production analytics implementation and compares the results against production outputs. If any production output differs from the upstream evidence, the release fails.

## Troubleshooting

- **Python not found**: Ensure Python 3.10+ is installed and available in your system's PATH.
- **PowerShell activation fails**: On Windows PowerShell, you may need to run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted` before activating the environment.
- **Missing `requirements.txt`**: Ensure you are executing commands from the repository root (`Brite/`), not the parent directory.
- **`ModuleNotFoundError` for `dirty_data`**: You must set your PYTHONPATH appropriately for your OS (e.g., `$env:PYTHONPATH="src"` on Windows or `export PYTHONPATH=src` on Linux/macOS).
- **Missing frozen artifacts**: Run `python -m dirty_data.freeze_artifacts` before `python run_s6_release.py`.
- **Disk/temp-space problems**: The test suite generates dynamic isolated environments. If you encounter disk space errors on your primary drive during testing, run pytest with a custom base temp directory (e.g., `python -m pytest -v --basetemp=D:\pytest_temp`).
