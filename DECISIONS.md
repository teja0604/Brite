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

## DEC-010 — Remediation Policy and Disposition Model
### Context
Phase 3 requires an auditable remediation layer that prepares data for analysis without silently dropping or inventing information.
### Options considered
1. Blanket cleaning (e.g. `df.dropna()`, `df.drop_duplicates()`, unrestricted categorical mapping).
2. Evidence-driven record-level dispositions (`AUTO_REPAIR`, `RETAIN_WITH_FLAG`, `EXCLUDE_FROM_ANALYSIS`, `UNRESOLVED`) that preserve exact provenance.
### Decision
Adopt the evidence-driven disposition model:
- **Dates**: Unambiguous variant dates are auto-repaired to YYYY-MM-DD. Ambiguous or invalid dates are retained as raw strings but flagged `eligible_for_duration_analysis=False`.
- **Identities**: Exact identical duplicates are collapsed (`AUTO_REPAIR`). Conflicting data or candidate variants are retained without merging.
- **Categories**: Only formatting-only variants (whitespace padding/casing differences, e.g., `Standard ` -> `Standard`) are auto-repaired. Semantic mappings (e.g., `Standard Case`, `Std.`) are strictly retained without inference, as candidate similarity does not prove semantic equivalence.
- **Missingness**: Left empty and unresolved rather than imputed. Expected missing values (e.g. closure date for Open cases) are explicitly retained.
- **Audit Logging**: The audit log (`cleaning_audit.csv`) focuses exclusively on material remediation events—actual transformations, analytic exclusions, exact duplicate drops, and explicitly unresolved issues. Canonical, unchanged values do not generate noise in the audit log.
- **Record-Level Status**: A precedence-based disposition (`EXCLUDE_FROM_ANALYSIS` -> `UNRESOLVED` -> `RETAIN_WITH_FLAG` -> `AUTO_REPAIR` -> `CLEAN`) is applied at the unique record level in `record_quality.csv` to distinguish action-level operations from final record state.
### Reasoning
A blanket clean drops nuance and destroys provenance. By evaluating eligibility per-record-per-analysis, we can safely compute case counts from records that have invalid dates, instead of entirely removing the record from the pipeline. Furthermore, formatting-only normalization is safe, but semantic normalization without explicit organizer mapping introduces false equivalence.
### Consequences
Generates a cleaned dataset that retains >99% of cases (dropping only 28 true duplicates), accompanied by a meticulous `cleaning_audit.csv` limited strictly to material interventions, and a `record_quality.csv` eligibility matrix for downstream analysis.

## DEC-011 — Phase 4 Analytical Framework & Denominator Discipline
### Context
Phase 4 demands robust, evidence-based answers to the operational questions, avoiding fabricated denominators, censorship biases, or unwarranted causal claims.
### Options considered
1. Naively computing average closure times and producing theoretical estimates.
2. Building an explicit eligibility rule engine for each question and transparently defining numerators and denominators.
### Decision
- **Unit of Analysis**: For closure duration, the unit is the unique case (`source_row` surviving exact deduplication).
- **Censorship Bias Prevention**: Direct comparison of average case durations heavily distorts recent performance (2025 cases haven't had time to become 300+ day cases). We define performance using the **30-day closure rate** alongside **Median Duration**, tracking cases that resolve quickly rather than averaging unbounded open cases.
- **Eligibility enforcement**: Any case flagged with `eligible_for_duration_analysis=False` (due to ambiguous formats, invalid calendars) or containing surviving temporal contradictions (`closure_date` < `intake_date`) is strictly excluded from the closure time denominator.
- **Unanswerable Questions**: Q3 asks about triage impacts on high-priority cases. We reject answering this mathematically because the `priority` field is 100% missing in 2023. We establish that we lack a pre-triage baseline.
### Reasoning
A transparent denominator policy prevents missing data from skewing percentages. Refusing to answer Q3 honors the instruction not to fabricate data. Preventing censorship bias ensures Q1 accurately reflects systemic slowdown rather than statistical mirages.
### Consequences
Generates a reproducible JSON/MD output that definitively proves Weybridge district is responsible for the systemic delay, provides highly defensible rates for 2023-2025, and explicitly challenges the feasibility of Q3 based on missing provenance.

## DEC-012 - Evidence and Reporting Layer
### Context
Phase 5 requires a verifiable, evaluator-facing evidence package that traces final conclusions back to raw rows, aggregates findings transparently, and ensures cross-phase reconciliation. 
### Options considered
1. Build a heavy UI dashboard or dynamic notebook.
2. Build a deterministic reporting layer that consumes upstream analytical artifacts and outputs static, machine-readable JSON and human-readable Markdown.
### Decision
Adopt the deterministic reporting layer (uild_reports.py). The pipeline consumes nalysis_results.json, aseline_profile.json, ecord_quality.csv, and cleaning_audit.csv. It explicitly verifies reconciliation (e.g., Raw Rows = Retained + Dropped) and throws clear errors if artifacts are missing or malformed. Causal language is explicitly excluded from Q2 interpretations.
### Reasoning
A static, deterministic reporting pipeline honors the reproducibility requirement and provides a clear lineage without obfuscating logic in a UI. Strict reconciliation checks ensure that no records are silently lost across phases.
### Consequences
Produces deterministic decision_evidence.md/json, data_quality_summary.md/json, cleaning_summary.md/json, and confidence_summary.json that fully reconcile with the dataset.
