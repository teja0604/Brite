# Phase 0 Engineering Decisions

## DEC-001 — Repository Structure
### Context
The original extraction contained archive metadata (`__MACOSX`, `.DS_Store`) and mixed the data with instructions. A clean structure is needed for reproducible data analysis without committing unwanted OS artifacts.
### Options considered
1. Keep the original extracted folder structure as is.
2. Reorganize into a standard data-science repository structure, isolating raw data from organizer docs and future code.
### Decision
Adopt a standard reproducible data-analysis layout (`data/raw/`, `src/`, `notebooks/`, `organizer/`).
### Reasoning
A reproducible pipeline requires strict separation of immutable source data, logic, and generated outputs. The extracted macOS artifacts must be removed and ignored as they pollute the codebase and provide no value.
### Trade-offs
Moving files changes their relative paths from the original zip. However, the instructions don't rely on hardcoded paths, making this safe.
### Consequences
Clear separation of concerns. The raw dataset is securely stored in `data/raw/` and is marked as immutable.

## DEC-002 — Treatment of Source Data
### Context
The CSV `case-export-2023-2025.csv` contains dirty data, including duplicate identities, inconsistent dates, impossible values, and an unusable category field.
### Options considered
1. Clean the CSV file manually and commit the cleaned version.
2. Treat the provided CSV as immutable evidence.
### Decision
The original CSV is strictly treated as immutable source evidence.
### Reasoning
Directly modifying the source data destroys the original state, making the analysis non-reproducible and obscuring the data quality assessment required by the handbook. All cleaning will be done programmatically in a later phase.
### Trade-offs
Requires programmatic transformations which take more code to write compared to quick manual fixes in Excel.
### Consequences
The analysis will be repeatable, and a robust cleaning log can be programmatically generated.

## DEC-003 — Architecture Selection for Phase 0
### Context
The prompt raised a question about whether persistent database infrastructure or frontend dashboards are needed.
### Options considered
1. Initialize a PostgreSQL/MySQL database and a web framework.
2. Retain a lightweight reproducible data-analysis pipeline (Jupyter notebooks/Python scripts).
### Decision
Proceed without database or frontend infrastructure.
### Reasoning
The organizer handbook explicitly states: "A notebook is a perfectly good delivery. No dashboard, no front end." and "Not required: A dashboard, a web app, or any interactive front end." The floor requirements emphasize repeatable cleaning and analytical answers, which can be fully satisfied by a reproducible Python pipeline.
### Trade-offs
If data scales drastically, a notebook might become slow. However, the dataset is small (~15,100 rows), so in-memory processing is perfectly adequate.
### Consequences
Development can focus exclusively on data cleaning and answering the operational questions, keeping the repository simple and adhering to the constraints.

# Phase 1 Engineering Decisions

## DEC-004 — Schema Validation Strategy
### Context
Before starting data cleaning, the pipeline needs to safely ingest the raw source and validate it matches our structural expectations.
### Options considered
1. Auto-parse dates and numerics during ingestion via pandas.
2. Read all data strictly as strings to prevent silent coercions.
### Decision
All ingestion reads the raw CSV strictly as strings (`dtype=str`) and validates only the presence of expected columns.
### Reasoning
Pandas can silently drop leading zeros or misinterpret ambiguous dates (e.g., swapping month/day) when parsing automatically. Reading as string preserves the raw representation identically so the data quality assessment reflects reality, not pandas' interpretation.
### Trade-offs
Requires explicit casting later in the cleaning phase.
### Consequences
The baseline profile correctly identifies the exact messy representations in the raw file without destroying evidence.

## DEC-005 — Baseline Profiling Separation
### Context
We need to profile the data to find issues.
### Options considered
1. Profile the data after cleaning it to show the "final" state.
2. Profile the raw data explicitly before any cleaning rules are applied.
### Decision
Profile the raw data strictly *before* any cleaning or identity resolution.
### Reasoning
The organizer explicitly requires a data quality assessment of the "badly maintained data export". Cleaning it first obscures the exact problems we need to report.
### Trade-offs
Raw profiling logic must handle dirty data gracefully without crashing.
### Consequences
We have generated a machine-verifiable `outputs/baseline_profile.json` and issue register that confirms duplicates, missing values, and date format variations exist in the source data.

## DEC-006 — Raw Data Preservation and Missing Values
### Context
During Phase 1 profiling, pandas automatically parses empty fields or strings like `NA` as `NaN`.
### Options considered
1. Allow pandas to handle missingness silently.
2. Read all fields without NA imputation, preserving empty strings `""` and literal text `NA`.
### Decision
The ingestion layer must preserve raw empty values as `""` and literal text exactly as-is (`keep_default_na=False`). Semantic missingness will be determined explicitly during profiling or cleaning.
### Reasoning
A string "NA" might mean something different than an empty field in a badly maintained dataset. By preserving the raw representation, the profiling correctly distinguishes between truly empty fields and literal "NA" or "unknown".
### Trade-offs
Empty string checks (`== ""`) must be explicitly written instead of generic `.isna()` checks.
### Consequences
The profiling logic now computes missing counts explicitly from `""`, keeping the ingestion layer purely representational.

## DEC-007 — Data Quality Contract and Anomaly Taxonomy
### Context
Phase 2 requires identifying dirty data without overwriting the raw baseline.
### Options considered
1. Detect anomalies and clean them in a single pass.
2. Separate detection (observation) from remediation (cleaning) via a formalized anomaly taxonomy.
### Decision
Adopt a strict separation between anomaly detection and data cleaning. Detected issues are tagged using an explicit `AnomalyType` taxonomy (`MISSING_VALUE`, `INVALID_DOMAIN`, `FORMAT_VIOLATION`, `LOGICAL_CONTRADICTION`, `IDENTITY_VARIANT`, `UNCONTROLLED_VOCABULARY`) and saved to an evidence register. No data is modified.
### Reasoning
A clear boundary prevents silent data loss and enables fully auditable remediation in future phases. Evaluators and stakeholders must be able to trace exactly why a record was classified as an anomaly based on explicit rules rather than opaque cleaning scripts.
### Trade-offs
Requires an intermediate storage/reporting layer for anomalies before the final cleaned dataset is produced.
### Consequences
The system produces a deterministic, verifiable log of anomalies (`outputs/phase2_anomaly_report.csv`) that serves as the factual basis for Phase 3 cleaning decisions.

## DEC-008 — Refining the Data Quality Contract
### Context
The initial Phase 2 rules were too aggressive, assuming frequency equated to canonical truth and that similar strings proved identity. The dataset's true nature required more conservative definitions.
### Options considered
1. Automatically merge similar identities and default to the top 5 categories as the only valid vocabulary.
2. Separate observation from assertion by distinguishing exact duplicates from candidate variants, and differentiating valid alternative date formats from invalid dates.
### Decision
Adopt conservative anomaly definitions:
- **Identity**: Distinguish `EXACT_DUPLICATE` from `CANDIDATE_IDENTITY_VARIANT` (matching via normalized signature). Phase 2 does not merge identities.
- **Vocabulary**: Distinguish `UNCONTROLLED_VOCABULARY` from `CANDIDATE_CATEGORY_VARIANT`. Rare categories are not marked as invalid merely because they are rare.
- **Dates**: Distinguish `DATE_FORMAT_VARIATION` (valid but non-canonical) from `INVALID_DATE` (unparseable). Ambiguous dates are not silently parsed. Temporal contradictions are only emitted if both dates are unambiguously canonical.
- **Traceability**: Every anomaly must include a `source_row` index back to the exact line in the raw CSV.
### Reasoning
Detecting a similar string is an observation; merging them is a decision. The anomaly register must provide evidence, not prematurely alter the dataset. Ambiguous dates (e.g. `03/04/2024`) cannot safely trigger logic rules until they are definitively interpreted.
### Consequences
The detector produces a richer, safer set of candidate variants without destroying the nuanced distinction between exact matches and probable matches. False positives are heavily reduced.

## DEC-009 — Deterministic Explicit Date Parsing
### Context
The previous classification of `DATE_FORMAT_VARIATION` fell back on `pandas.to_datetime` (flexible inference). This allowed undocumented inference rules (e.g. implicitly assuming a locale like month-first) to silently interpret ambiguous dates, producing a pandas warning during tests.
### Options considered
1. Suppress the warning and accept the parser's guess.
2. Replace flexible inference with explicit, deterministic rules that match the actual formats found in the dataset.
### Decision
Removed unrestricted `pd.to_datetime` inference. Date classification is now strictly deterministic:
- `CANONICAL`: matched by `YYYY-MM-DD` and validated by `datetime.strptime`.
- `DATE_FORMAT_VARIATION`: exactly matched to textual `Month DD, YYYY`, or matched as an unambiguous numeric format where one component explicitly exceeds 12.
- `AMBIGUOUS_DATE_FORMAT`: numeric dates where both day/month parts are `<= 12` are marked ambiguous.
- `INVALID_DATE`: fails physical calendar validation or format parsing.
### Reasoning
A data-quality pipeline cannot confidently assert anomaly classifications based on silent inference rules. By explicitly enumerating the formats present in the dataset and deterministically checking ambiguity, we prevent false certainty.
### Consequences
Testing produces no pandas warnings. Unambiguous numeric and explicit text formats are accurately mapped without locale guesswork.
