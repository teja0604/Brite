# Phase 0 Engineering Decisions

## DEC-001 â€” Repository Structure
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

## DEC-002 â€” Treatment of Source Data
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

## DEC-003 â€” Architecture Selection for Phase 0
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

## DEC-004 â€” Schema Validation Strategy
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

## DEC-005 â€” Baseline Profiling Separation
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

## DEC-006 â€” Raw Data Preservation and Missing Values
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

## DEC-007 â€” Data Quality Contract and Anomaly Taxonomy
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

## DEC-008 â€” Refining the Data Quality Contract
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

## DEC-009 â€” Deterministic Explicit Date Parsing
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

## DEC-010 â€” Remediation Policy and Disposition Model
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
- **Audit Logging**: The audit log (`cleaning_audit.csv`) focuses exclusively on material remediation eventsâ€”actual transformations, analytic exclusions, exact duplicate drops, and explicitly unresolved issues. Canonical, unchanged values do not generate noise in the audit log.
- **Record-Level Status**: A precedence-based disposition (`EXCLUDE_FROM_ANALYSIS` -> `UNRESOLVED` -> `RETAIN_WITH_FLAG` -> `AUTO_REPAIR` -> `CLEAN`) is applied at the unique record level in `record_quality.csv` to distinguish action-level operations from final record state.
### Reasoning
A blanket clean drops nuance and destroys provenance. By evaluating eligibility per-record-per-analysis, we can safely compute case counts from records that have invalid dates, instead of entirely removing the record from the pipeline. Furthermore, formatting-only normalization is safe, but semantic normalization without explicit organizer mapping introduces false equivalence.
### Consequences
Generates a cleaned dataset that retains >99% of cases (dropping only 28 true duplicates), accompanied by a meticulous `cleaning_audit.csv` limited strictly to material interventions, and a `record_quality.csv` eligibility matrix for downstream analysis.

## DEC-011 â€” Phase 4 Analytical Framework & Denominator Discipline
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
Adopt the deterministic reporting layer ( uild_reports.py). The pipeline consumes  nalysis_results.json,  aseline_profile.json, ecord_quality.csv, and cleaning_audit.csv. It explicitly verifies reconciliation (e.g., Raw Rows = Retained + Dropped) and throws clear errors if artifacts are missing or malformed. Causal language is explicitly excluded from Q2 interpretations.
### Reasoning
A static, deterministic reporting pipeline honors the reproducibility requirement and provides a clear lineage without obfuscating logic in a UI. Strict reconciliation checks ensure that no records are silently lost across phases.
### Consequences
Produces deterministic decision_evidence.md/json, data_quality_summary.md/json, cleaning_summary.md/json, and confidence_summary.json that fully reconcile with the dataset.

## DEC-013 - Adversarial Hardening & Safe Execution
### Context
Adversarial validation (Phase 6) revealed that edge cases (like zero eligible records resulting in empty DataFrames) caused Pandas `apply()` to return an empty Series, breaking downstream filtering. Furthermore, the reporting layer hardcoded its artifact source directory, meaning tests could inadvertently read the real artifacts and swallow failures when testing missing upstream files.
### Problem discovered
Zero-row dataframes crashed `analyze.py`, and `build_reports.py` masked missing inputs by hardcoding the output directory.
### Options considered
1. Catch the KeyError or ValueError at the top level and fail.
2. Fix the lowest-level logic by bypassing operations on empty DataFrames and decoupling output directories from script locations.
### Decision
Adopt lowest-level logic fixes: `analyze.py` checks `df.empty` before applying row-level functions to gracefully retain empty structures, preventing division-by-zero or KeyError crashes. `build_reports.py` was refactored to dynamically accept the output directory path via `sys.argv`, enabling true test isolation.
### Reasoning
Handling failures at the source instead of broadly catching exceptions ensures the pipeline fails loudly where appropriate (missing input files) but handles valid edge cases safely (zero eligible records).
### Trade-offs
Adds minor structural complexity to pandas operations (explicit `.empty` checks instead of relying on vectorized safety nets), but guarantees robustness under extreme filtering.
### Consequences
Pipeline now survives zero-record scenarios without crashing or producing misleading NaNs, and testing can safely isolate and verify failure behavior on missing files.

## DEC-014 - Strict Dependency Management
### Context
The project imported numpy directly in analyze.py. While numpy is typically installed implicitly alongside pandas, relying on transitive dependencies introduces reproducibility risks across different package manager resolutions.
### Options considered
1. Leave requirements.txt relying only on pandas.
2. Explicitly declare numpy in requirements.txt.
### Decision
Explicitly add numpy to requirements.txt.
### Reasoning
Reproducibility requires explicit top-level tracking of any package directly imported by the source code, preventing future environmental breakage.
### Consequences
The environment is fully deterministic regarding top-level package imports, eliminating implicit dependency assumptions.

## DEC-014 - Portable Execution Architecture
### Context
Evaluators must be able to run the pipeline sequentially from a clean clone using standard Python execution (e.g. `python src/dirty_data/profile.py`) without having to manually set the PYTHONPATH environment variable or install the project as a package.
### Options considered
1. Force the evaluator to set PYTHONPATH.
2. Create a setup.py / pyproject.toml to install the package.
3. Inject sys.path resolution into the entrypoint scripts.
### Decision
Adopt sys.path injection (`sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`) into the entrypoint scripts.
### Reasoning
This is the minimal, least-intrusive fix. It avoids forcing the evaluator to configure environment variables and eliminates packaging complexity that isn't required for a simple data analysis pipeline.
### Consequences
The pipeline runs completely isolated out-of-the-box on any OS without ModuleNotFoundError for internal dirty_data imports.

## DEC-015 â€” Surprise Source Contracts (S1 Part A)
### Context
The Surprise Challenge introduced a second source dataset with a different schema and missing fields. We need to validate and ingest this data without contaminating the frozen, verified logic of the original pipeline.
### Options considered
1. Weaken the original schema by making fields optional or changing their expected names to accommodate the new source.
2. Define a separate supplementary source contract and keep the original contract intact.
### Decision
Keep the original contract exactly as it is (`ORIGINAL_SCHEMA`) and define a separate `SUPPLEMENTARY_SCHEMA` that exactly matches the expectations of the new source (including missing `status`, `client_ref`, and `contact_count`).
### Reasoning
Source-specific contracts prevent schema drift from contaminating the original pipeline. It forces us to handle the structural differences explicitly in a later canonical mapping phase rather than silently guessing or inventing mappings at the ingestion layer.
### Consequences
We can now ingest and validate both sources deterministically according to their own rules, which enables a safe canonical transformation and field-level reconciliation in subsequent phases.

## DEC-016 — Canonical Data Model (S1 Part B)
### Context
The original and supplementary datasets have fundamentally different schemas (e.g. `case_id` vs `reference`, missing `status` and `client_ref` in supplementary). We need a unified structure to enable automated field-level comparison and reconciliation.
### Options considered
1. Force the supplementary dataset into the original schema structure during ingestion.
2. Create a third, distinct Canonical Schema that explicitly models the shared business concepts without dictating source precedence.
### Decision
Adopt a distinct Canonical Schema (`CANONICAL_SCHEMA`). We define semantic mappings for each field. Crucially, `status` is modeled as a conceptually derived field based on the presence of `closure_date`. Fields absent in one source (like `contact_count`) are allowed to be explicitly marked unavailable rather than imputed as zero.
### Reasoning
A dedicated canonical model separates the "vocabulary" problem from the "reconciliation" problem. By retaining distinction between a missing source field and an empty field, we prevent silent data loss. Avoiding precedence rules at this layer ensures the model remains neutral for later conflict resolution.
### Consequences
The system now has a defined target structure for the future Source Adapters (Phase S2) to map into, ensuring both datasets can be compared apples-to-apples in Phase S6.


## DEC-017 — Original Source Canonical Adapter (S2 Part A)
### Context
We must translate the Original dataset into the Canonical Schema defined in S1 Part B without destroying the frozen analytical baseline or prematurely mixing datasets.
### Options considered
1. Integrate the adapter directly into the existing ingestion or detection pipeline.
2. Build a standalone, deterministic adapter module strictly scoped to structure mapping.
### Decision
Adopt a standalone, isolated adapter module (`src/dirty_data/adapter.py`). The adapter merely filters and enriches the original dataframe with canonical metadata (`source_system` = ORIGINAL, `source_row_index`) without replacing the original ingestion/cleaning pipeline behavior.
### Reasoning
Keeping the adapter isolated ensures 100% backward compatibility with the existing Q1/Q2/Q3 logic. It preserves empty strings rather than imputing defaults, and it faithfully forwards the original `status` column without blindly re-evaluating malformed dates. This adheres strictly to the rule that an adapter translates but does not validate or reconcile.
### Consequences
The original data can now be transformed into canonical records on demand for later S6 reconciliation without polluting the existing Phase 0-7 operational pipeline.


## DEC-018 — Supplementary Source Canonical Adapter (S2 Part B)
### Context
The Supplementary Source must be mapped into the CANONICAL_SCHEMA to enable later reconciliation. It lacks several fields (status, contact_count, client_ref) and uses a different structural vocabulary (e.g., reference vs case_id).
### Options considered
1. Merge the supplementary mapping directly into the existing ingestion or detection pipeline.
2. Merge the datasets early inside the adapter layer.
3. Extend the isolated adapter architecture with a source-specific supplementary adapter.
### Decision
Adopt Option 3. Implemented `adapt_supplementary_to_canonical` in `adapter.py`. This strictly preserves the supplementary source's exact structure, mapping fields 1:1 where they exist, and mapping missing fields to empty strings (not artificial zeroes or defaults). We derive `status` safely: EMPTY closure -> Open, VALID closure -> Closed, INVALID/AMBIGUOUS -> empty string (refusing to manufacture certainty).
### Reasoning
Separation of concerns is maintained. The supplementary adapter performs deterministic mapping without silently correcting anomalies or merging datasets. It handles missing values safely and preserves the actual `extract_date` (2026-01-14). Maintaining source evidence preserves downstream options for the reconciliation layer.
### Consequences
Both sources can now be safely translated into a shared vocabulary (Canonical Schema). Identity matching, field comparison, and reconciliation (S3+) can now compare equivalent structures without dealing with structural noise. Deduplication and conflict resolution remain intentionally deferred.


## DEC-019 — Identity Matching Logic (S3)
### Context
The canonical Original and Supplementary datasets must be associated based on their identity without resolving conflicts, overriding values, or artificially deduplicating data.
### Options considered
1. Use \pd.merge(how='outer')\ to join on \case_id\, resulting in side-by-side columns (e.g., \status_x\, \status_y\).
2. Use a hierarchical data structure (e.g., dictionary) to map \case_id\ to a list of source records.
3. Use a flat concatenated DataFrame, sorted deterministically by \case_id\, \source_system\, and \source_row_index\.
### Decision
Adopt Option 3. Implemented \match_identities\ in \identity.py\. It calculates the overlap metrics dynamically, then strictly concatenates both canonical DataFrames and sorts them. This maintains the 1:1 structural schema (preventing column bloat from merges) and groups conflicting records neatly as adjacent rows.
### Reasoning
Concatenation avoids silent merges or drops. It enforces that identity matching is purely a grouping exercise, not a resolution exercise. Provenance (\source_system\, \source_row_index\) acts as the differentiator within the grouped identity ledger.
### Consequences
The resulting \ligned_df\ has exactly \len(orig) + len(supp)\ rows (19,280). No data is lost, and S4/S5 field comparisons can process conflicts sequentially by iterating over \groupby('case_id')\.


## DEC-020 — Phase S3 Correction: Explicit Identity Index
### Context
The initial S3 implementation successfully created a safe, non-destructive identity ledger by concatenating physical records grouped by \case_id\. However, a human review identified that this ledger alone did not fulfill the requirement to explicitly expose the identity match relationship. Downstream modules would have been forced to re-derive match status and cardinality from the physical ledger, violating separation of concerns.
### Decision
S3 now produces two complementary artifacts: \ligned_df\ (the physical identity ledger) and \identity_index_df\ (the identity match result). The index contains exactly one row per unique \case_id\, describing \original_count\, \supplementary_count\, \match_status\, and \cardinality\.
### Reasoning
- **Why the ledger alone was insufficient**: The ledger preserves raw data but hides relationship semantics. An explicit identity index explicitly answers 'Which records represent the same case?'
- **Why identity classification belongs in S3**: Identity Matching is S3's exact domain boundary. Deferring cardinality calculation to S4 would incorrectly entangle identity derivation with field-level conflict detection.
- **Why cardinality is descriptive only & no deduplication occurs**: S3's job is purely associational. Deduplicating records (e.g., resolving a `MANY_TO_ONE` identity) forces a source precedence decision, which violates the strict rule that S3 establishes equivalence without deciding which source is correct.
- **Why no source precedence is encoded**: The Identity Index describes mathematical multiplicity (e.g., 2 Original records, 1 Supplementary record) neutrally. It does not dictate which record 'wins'.
- **Why the physical ledger remains unchanged**: The `pd.concat` approach perfectly preserves the physical 19,280 rows and their provenance (`source_system`, `source_row_index`) for future reconciliation phases.
### Consequences
The original 19,280-row `aligned_df` is fully preserved. The new `identity_index_df` allows subsequent phases to instantly route cases based on deterministic, pre-calculated cardinality rules. MANY_TO_ONE identifies that multiple physical records exist on one source side. It does not itself authorize deduplication. Later comparison/reconciliation phases must explicitly determine how those records are handled while preserving the audit trail and avoiding silent record loss.

## DEC-021: Phase S4 Field-Level Comparison

### Date
2026-08-23

### Context
Phase S4 requires comparing fields from the Original and Supplementary canonical records, strictly generating evidence without deducing a winning source. We must classify conflicts, exact matches, and differentiate between missing values and unavailable fields. 

### Decision
1. **Comparison Taxonomy**: S4 classifies all pairwise field comparisons into: EXACT_MATCH, REPRESENTATION_EQUIVALENT, CONFLICT, MISSING_ONE_SIDE, UNAVAILABLE_ONE_SIDE, INVALID_COMPARISON, and NOT_COMPARABLE.
2. **Missing vs Unavailable**: We distinguish between a field existing but being empty (MISSING_ONE_SIDE) and a field conceptually absent in the source schema (e.g., contact_count in Supplementary) which results in UNAVAILABLE_ONE_SIDE.
3. **Date Comparison**: Dates are parsed using existing utilities. If formats differ but the underlying day is identical, we classify as REPRESENTATION_EQUIVALENT. Ambiguous and malformed dates are flagged as INVALID_COMPARISON without arbitrary guessing.
4. **Status Comparison**: Derived supplementary statuses are compared semantically with original statuses.
5. **Provenance**: Every physical row comparison preserves original_source_row and supplementary_source_row.
6. **Multi-Record Cardinality**: For identities with multiple physical records, S4 uses Cartesian comparison to generate exhaustive comparison evidence across all Original × Supplementary physical-record combinations. These combinations are comparison candidates only; they do not establish confirmed physical-record correspondence or authorize deduplication. Human review approved this comparison strategy.
7. **No Precedence**: S4 creates an artifact of evidence only. There is no 'winner' field.

### Consequences
S4 outputs a deterministic comparison matrix preserving all physical evidence and explicitly mapping structural disparities across both datasets without making reconciliation decisions.


## DEC-022: Phase S5 Reconciliation Policy

### Date
2026-08-23

### Status
HUMAN APPROVED

### Context
Phase S5 requires building a deterministic reconciliation policy that converts the evidence produced by S4 into explicit field-level reconciliation decisions. Because there are no existing business rules authorizing source precedence or deduplication, these ambiguities required explicit human review before becoming official policy.

### AI Contribution
1. **Identified the 5 reconciliation ambiguities**: Field-level conflicts, missing value imputation, representation equivalents, unavailable fields, and multi-record identities (`MANY_TO_ONE`).
2. **Proposed initial deterministic rules** for each ambiguity, awaiting explicit human approval.

### My Contribution & Verification (Human Approved)
I explicitly reviewed and approved the following reconciliation rules:
1. **Field-level precedence**: The Supplementary source wins ONLY for `status` and `closure_date`. The Original source wins for all other fields (`district`, `intake_date`, `category`, `priority`, `caseworker_id`, `client_ref`, `contact_count`). The extraction date (`extract_date`) is not treated as an ordinary business field conflict, but as an explicit provenance record where the original blank value is retained alongside the supplementary extraction date in the audit logs.
2. **Missing-value handling**: Use the populated value from the available side (`MISSING_ONE_SIDE`), preserve original missingness in audit trail, and explicitly record that imputation occurred.
3. **Representation-equivalent handling**: Keep the Original string representation without silently normalizing the raw evidence.
4. **Unavailable-field handling**: Use the value from the source that actually contains the field, without interpreting it as a missing value.
5. **MANY_TO_ONE preservation strategy**: Produce exactly one reconciled output row per Original physical record. Pair each Original physical record with the single Supplementary record for that identity and apply field-level rules independently. `ONE_TO_MANY` and `MANY_TO_MANY` identities are strictly marked as requiring explicit multi-record handling (`UNRESOLVED_MULTI_RECORD`).

### Consequences
The reconciled dataset deterministically resolves field-level conflicts. The 46 `MANY_TO_ONE` identities preserve Original physical-row cardinality, but their analytical values may change according to the explicitly approved field-level reconciliation rules. No silent record loss occurs, and the audit trail captures all decisions with explicit provenance tracking.
