# AI Usage Log

This document records meaningful AI-assisted engineering work. AI was used as an engineering support tool for analysis and review. I retained responsibility for the final engineering decisions and checked recommendations against the organizer material and actual project state.

## Phase 0 Ã¢â‚¬â€� Requirements and Architecture Review

### Requirement interpretation

AI contribution:
Extracted key constraints and deliverables from the organizer handbook, particularly the requirement for a repeatable pipeline and comprehensive cleaning log rather than just an end result.

My verification:
I reviewed the organizer handbook and challenge questions to ensure no requirements were missed or hallucinated before accepting the interpretation.

Final decision:
Adopted a reproducible data-analysis repository structure rather than a quick script approach, ensuring the final delivery meets the rubric's standard for reproducibility.

### Data-quality assessment

AI contribution:
Profiled the raw dataset (`case-export-2023-2025.csv`) to highlight significant data quality risks described in the prompt, such as duplicate identities and inconsistent dates.

My verification:
I reviewed the supplied dataset and organizer documentation to confirm the relevant data-quality issues before finalizing the repository setup.

Final decision:
Established a strict immutability rule for the source CSV. All data cleaning will be implemented programmatically in Phase 1 to maintain a verifiable cleaning log.

### Architecture evaluation

AI contribution:
Evaluated whether the operational questions required persistent database infrastructure or frontend development based on the dataset size and requirements.

My verification:
I checked the delivery constraints in the organizer material, including the statement that a notebook is an acceptable delivery and that no dashboard/frontend is required.

Final decision:
Decided against initializing a database or web framework. The solution will rely exclusively on a reproducible notebook or Python pipeline to prevent over-engineering.

### Ambiguity identification

AI contribution:
Flagged ambiguous terminology in the organizer material, specifically regarding how "duplicate identities" and "uncontrolled free text" are defined.

My verification:
I reviewed the relevant challenge wording and confirmed that these definitions were intentionally left unspecified to test analytical judgment.

Final decision:
Documented these ambiguities to be addressed empirically during the Phase 1 exploratory data analysis rather than making premature assumptions.

## Phase 1 Ã¢â‚¬â€� Data Ingestion and Baseline Profiling

### Schema validation design

AI contribution:
Recommended reading all columns as raw strings during ingestion to prevent pandas from silently coercing dates or dropping leading zeros from IDs.

My verification:
I reviewed the organizer handbook's warning ("be careful about what you drop silently") and confirmed that preserving the raw text representation is necessary for an honest data quality assessment.

Final decision:
Implemented the ingestion module to read the CSV as purely strings and built explicit test cases to verify this behavior.

### Profiling dimension selection

AI contribution:
Suggested separating the profiling of exact identifier duplicates (like `case_id`) from exploratory profiling of categories and dates to establish clear evidence for later resolution.

My verification:
I reviewed the profiling requirements and confirmed that identifying exact duplicates without merging them aligns with the Phase 1 goal of establishing a baseline without prematurely altering the dataset.

Final decision:
Designed the `profile.py` module to generate a deterministic JSON profile of raw values without applying any analytical cleaning.

### Reproducibility and Data Provenance Correction

AI contribution:
Identified that pandas random sampling and automatic NA coercion violated the strict deterministic and immutable raw-evidence constraints. Recommended updating ingestion to explicitly preserve empty strings and literal "NA" values, and replacing random sampling with deterministic selection.

My verification:
I reviewed the reproducibility requirement and the organizer's instruction that "a parser that skips rows it cannot read... will not tell you it did that." I verified that preserving empty strings explicitly avoids silent data loss.

Final decision:
Refactored the ingestion and profiling modules to guarantee deterministic outputs and literal raw value preservation.

## Phase 2 Ã¢â‚¬â€� Data Quality Contract & Anomaly Taxonomy

### Detection and Cleaning Separation

AI contribution:
Proposed a formal taxonomy (e.g., `LOGICAL_CONTRADICTION`, `UNCONTROLLED_VOCABULARY`) to classify errors without modifying the underlying raw dataset, ensuring the "observe and detect" phase is cleanly separated from the "propose and clean" phase.

My verification:
I reviewed the requirement to "NOT clean or overwrite raw data in this phase" and confirmed that the generated evidence-backed register fulfills the auditability mandate by logging exact anomalies and severity levels without prematurely altering values.

Final decision:
Implemented the `Anomaly` dataclass and detector engine to output a deterministic anomaly register based on strict data quality contract rules.

### Phase 2 Contract Refinement

AI contribution:
AI review identified that the top-five category heuristic and aggressive identifier normalization could create false positives. Proposed refining the taxonomy to distinguish exact duplicates from candidate identity variants, and valid alternative date formats from invalid dates.

My verification:
I checked the implementation against the organizer's actual wording and the generated evidence. I verified that rare categories are no longer prematurely penalized, ambiguous dates are not silently parsed, and every anomaly now includes a strict `source_row` back to the raw CSV.

Final decision:
Amended the Phase 2 commit to enforce conservative, evidence-only detection, removing all automatic data-merging heuristics.

### Phase 2 Ambiguous Date Parsing Correction

AI contribution:
AI review recognized that a flexible date parser could silently misinterpret ambiguous numeric dates (e.g., `03/04/2024` as April 3 or March 4). Implemented a deterministic format check to catch dates where both numeric components are `<= 12` and explicitly label them as `AMBIGUOUS_DATE_FORMAT` without guessing their semantics.

My verification:
I reviewed the test output and the new anomaly register. I verified that ambiguous strings are safely tagged rather than being silently converted to incorrect dates, guaranteeing that temporal contradiction checks are restricted solely to unambiguous timestamps.

Final decision:
Refined the date detection logic to add `AMBIGUOUS_DATE_FORMAT` to the taxonomy and isolated it from temporal logic checks.

### Phase 2 Deterministic Date Parsing

AI contribution:
AI review recognized that relying on pandas flexible inference for `DATE_FORMAT_VARIATION` parsing introduced undocumented locale assumptions and warnings. Proposed replacing it with explicit `datetime.strptime` calls tailored only to the formats actually present in the CSV.

My verification:
I reviewed the dataset formats and the updated `contract.py` parser, ensuring that the explicit checks strictly enforce calendar rules without silently guessing when numeric dates could be ambiguous. The test suite warning is resolved.

Final decision:
Refactored date parsing to use deterministic rules exclusively, removing `pandas.to_datetime` inference from the contract layer.

### Phase 3 Remediation Policy & Audit

AI contribution:
AI assisted in designing the remediation policy and the four-tier disposition model (`AUTO_REPAIR`, `RETAIN_WITH_FLAG`, `EXCLUDE_FROM_ANALYSIS`, `UNRESOLVED`). Challenged the blanket assumption that records with invalid dates should be dropped entirely, proposing instead a per-record eligibility matrix (`record_quality.csv`) so that invalid dates are merely excluded from duration analysis but retained for total case count calculations.

My verification:
I reviewed the disposition definitions, verified the unit tests testing exact duplicate detection, and analyzed the real data reconciliation metrics. I confirmed that the strict separation of detection (Phase 2) from explicit remediation rules prevents undocumented transformations, and that the idempotency and source-row tracking satisfy the auditability requirements.

Final decision:
Implemented the auditable remediation layer, explicit rule set, and dual-output (cleaned dataset + audit log) architecture as the official Phase 3 deliverable.

### Phase 3 Correction

AI contribution:
Identified that the current category normalization crossed the boundary from formatting normalization into unsupported semantic inference and that remediation counts were mixing action-level and record-level units.

My verification:
Reviewed the implementation and checked the remediation behavior against the Phase 2 evidence-first policy and generated outputs.

Final decision:
Restricted automatic category normalization to formatting-only cases and separated action-level audit metrics from record-level disposition metrics.

### Phase 4 Decision Analysis & Metric Definitions

AI contribution:
AI assisted in defining rigorous numerators, denominators, and eligibility logic for the organizer questions. It identified censorship bias in directly comparing average case durations and recommended the 30-day closure rate and median duration as unbiased indicators. It also correctly identified that Question 3 was unanswerable because the `priority` field was 100% missing in 2023, thus preventing the establishment of a pre-triage baseline.

My verification:
I reviewed the code implementation (`analyze.py`, `analysis_spec.py`), the mathematical formulations in the JSON/MD output, and executed tests verifying that the 126 temporal contradictions skipped during parsing were securely excluded during analysis. I validated that the data limitations identified for Q3 matched the actual missingness in the CSV.

Final decision:
Approved the analytical pipeline, established Weybridge as the driver of performance degradation, and definitively ruled Q3 unanswerable with the provided dataset.

### Phase 5 â€” Reproducible Evidence Reporting
**AI contribution:**
Designed the deterministic reporting architecture (uild_reports.py) to trace final analytical conclusions back to raw anomaly and remediation outputs. Extracted required lineage constraints and enforced explicit cross-phase mathematical reconciliation. Implemented a robust testing layer checking immutability, determinism, and absence of causal language.
**My verification:**
Reviewed the generated Markdown reports for readability and tone. Verified the reconciliation logic manually (Raw Rows = Retained + Dropped). Checked that the deterministic execution produces the exact same output bytes upon repeated runs, free of absolute paths.
**Final decision:**
Approved the reporting layer to serve as the evaluator-facing evidence package, confirming it does not silently discard data or hallucinate results.

### Phase 6 - Adversarial Validation & System Hardening
**AI contribution:**
AI assisted in designing adversarial failure categories (schema, missingness, large-input, missing upstream files) and implementing isolated test suites using Pytest temporary directories. It identified unsafe behavior in nalyze.py (empty DataFrame apply crash) and uild_reports.py (hardcoded artifact path swallowing test failures).
**My verification:**
Verified the defects existed by running the adversarial test suite and confirming failures. Validated that the underlying fixes (gracefully checking df.empty and utilizing sys.argv[1] for output targets) correctly resolved the vulnerabilities without breaking the real data pipeline.
**Final decision:**
Approved the hardening modifications as they prevent loud failure from missing files and silent failure/crashes from extreme downstream filtering.

### Phase 7 - Final Reproducibility & Submission Gate
**AI contribution:**
AI assisted in performing a comprehensive repository and dependency audit. It identified that numpy was directly imported in the source code but only implicitly provided via pandas, introducing a reproducibility risk.
**My verification:**
Verified the import traces using grep and confirmed numpy was missing from requirements.txt. Validated the addition of numpy to the requirements file to ensure explicit tracking.
**Final decision:**
Approved the strict dependency management approach to guarantee portable environment construction.

### Phase 7 - Clean-Clone Reproducibility
**AI contribution:**
AI assisted in creating a clean-clone isolation test environment outside the repository. It executed the entire pipeline from a fresh clone, verified cross-phase mathematical reconciliation, verified SHA-256 integrity, and ensured deterministic execution without hidden environmental dependencies. It identified that python src/dirty_data/*.py executions failed due to Python's module path resolution and provided a minimal sys.path injection fix to make the repository fully portable.
# AI Usage Log

This document records meaningful AI-assisted engineering work. AI was used as an engineering support tool for analysis and review. I retained responsibility for the final engineering decisions and checked recommendations against the organizer material and actual project state.

## Phase 0 â€” Requirements and Architecture Review

### Requirement interpretation

AI contribution:
Extracted key constraints and deliverables from the organizer handbook, particularly the requirement for a repeatable pipeline and comprehensive cleaning log rather than just an end result.

My verification:
I reviewed the organizer handbook and challenge questions to ensure no requirements were missed or hallucinated before accepting the interpretation.

Final decision:
Adopted a reproducible data-analysis repository structure rather than a quick script approach, ensuring the final delivery meets the rubric's standard for reproducibility.

### Data-quality assessment

AI contribution:
Profiled the raw dataset (`case-export-2023-2025.csv`) to highlight significant data quality risks described in the prompt, such as duplicate identities and inconsistent dates.

My verification:
I reviewed the supplied dataset and organizer documentation to confirm the relevant data-quality issues before finalizing the repository setup.

Final decision:
Established a strict immutability rule for the source CSV. All data cleaning will be implemented programmatically in Phase 1 to maintain a verifiable cleaning log.

### Architecture evaluation

AI contribution:
Evaluated whether the operational questions required persistent database infrastructure or frontend development based on the dataset size and requirements.

My verification:
I checked the delivery constraints in the organizer material, including the statement that a notebook is an acceptable delivery and that no dashboard/frontend is required.

Final decision:
Decided against initializing a database or web framework. The solution will rely exclusively on a reproducible notebook or Python pipeline to prevent over-engineering.

### Ambiguity identification

AI contribution:
Flagged ambiguous terminology in the organizer material, specifically regarding how "duplicate identities" and "uncontrolled free text" are defined.

My verification:
I reviewed the relevant challenge wording and confirmed that these definitions were intentionally left unspecified to test analytical judgment.

Final decision:
Documented these ambiguities to be addressed empirically during the Phase 1 exploratory data analysis rather than making premature assumptions.

## Phase 1 â€” Data Ingestion and Baseline Profiling

### Schema validation design

AI contribution:
Recommended reading all columns as raw strings during ingestion to prevent pandas from silently coercing dates or dropping leading zeros from IDs.

My verification:
I reviewed the organizer handbook's warning ("be careful about what you drop silently") and confirmed that preserving the raw text representation is necessary for an honest data quality assessment.

Final decision:
Implemented the ingestion module to read the CSV as purely strings and built explicit test cases to verify this behavior.

### Profiling dimension selection

AI contribution:
Suggested separating the profiling of exact identifier duplicates (like `case_id`) from exploratory profiling of categories and dates to establish clear evidence for later resolution.

My verification:
I reviewed the profiling requirements and confirmed that identifying exact duplicates without merging them aligns with the Phase 1 goal of establishing a baseline without prematurely altering the dataset.

Final decision:
Designed the `profile.py` module to generate a deterministic JSON profile of raw values without applying any analytical cleaning.

### Reproducibility and Data Provenance Correction

AI contribution:
Identified that pandas random sampling and automatic NA coercion violated the strict deterministic and immutable raw-evidence constraints. Recommended updating ingestion to explicitly preserve empty strings and literal "NA" values, and replacing random sampling with deterministic selection.

My verification:
I reviewed the reproducibility requirement and the organizer's instruction that "a parser that skips rows it cannot read... will not tell you it did that." I verified that preserving empty strings explicitly avoids silent data loss.

Final decision:
Refactored the ingestion and profiling modules to guarantee deterministic outputs and literal raw value preservation.

## Phase 2 â€” Data Quality Contract & Anomaly Taxonomy

### Detection and Cleaning Separation

AI contribution:
Proposed a formal taxonomy (e.g., `LOGICAL_CONTRADICTION`, `UNCONTROLLED_VOCABULARY`) to classify errors without modifying the underlying raw dataset, ensuring the "observe and detect" phase is cleanly separated from the "propose and clean" phase.

My verification:
I reviewed the requirement to "NOT clean or overwrite raw data in this phase" and confirmed that the generated evidence-backed register fulfills the auditability mandate by logging exact anomalies and severity levels without prematurely altering values.

Final decision:
Implemented the `Anomaly` dataclass and detector engine to output a deterministic anomaly register based on strict data quality contract rules.

### Phase 2 Contract Refinement

AI contribution:
AI review identified that the top-five category heuristic and aggressive identifier normalization could create false positives. Proposed refining the taxonomy to distinguish exact duplicates from candidate identity variants, and valid alternative date formats from invalid dates.

My verification:
I checked the implementation against the organizer's actual wording and the generated evidence. I verified that rare categories are no longer prematurely penalized, ambiguous dates are not silently parsed, and every anomaly now includes a strict `source_row` back to the raw CSV.

Final decision:
Amended the Phase 2 commit to enforce conservative, evidence-only detection, removing all automatic data-merging heuristics.

### Phase 2 Ambiguous Date Parsing Correction

AI contribution:
AI review recognized that a flexible date parser could silently misinterpret ambiguous numeric dates (e.g., `03/04/2024` as April 3 or March 4). Implemented a deterministic format check to catch dates where both numeric components are `<= 12` and explicitly label them as `AMBIGUOUS_DATE_FORMAT` without guessing their semantics.

My verification:
I reviewed the test output and the new anomaly register. I verified that ambiguous strings are safely tagged rather than being silently converted to incorrect dates, guaranteeing that temporal contradiction checks are restricted solely to unambiguous timestamps.

Final decision:
Refined the date detection logic to add `AMBIGUOUS_DATE_FORMAT` to the taxonomy and isolated it from temporal logic checks.

### Phase 2 Deterministic Date Parsing

AI contribution:
AI review recognized that relying on pandas flexible inference for `DATE_FORMAT_VARIATION` parsing introduced undocumented locale assumptions and warnings. Proposed replacing it with explicit `datetime.strptime` calls tailored only to the formats actually present in the CSV.

My verification:
I reviewed the dataset formats and the updated `contract.py` parser, ensuring that the explicit checks strictly enforce calendar rules without silently guessing when numeric dates could be ambiguous. The test suite warning is resolved.

Final decision:
Refactored date parsing to use deterministic rules exclusively, removing `pandas.to_datetime` inference from the contract layer.

### Phase 3 Remediation Policy & Audit

AI contribution:
AI assisted in designing the remediation policy and the four-tier disposition model (`AUTO_REPAIR`, `RETAIN_WITH_FLAG`, `EXCLUDE_FROM_ANALYSIS`, `UNRESOLVED`). Challenged the blanket assumption that records with invalid dates should be dropped entirely, proposing instead a per-record eligibility matrix (`record_quality.csv`) so that invalid dates are merely excluded from duration analysis but retained for total case count calculations.

My verification:
I reviewed the disposition definitions, verified the unit tests testing exact duplicate detection, and analyzed the real data reconciliation metrics. I confirmed that the strict separation of detection (Phase 2) from explicit remediation rules prevents undocumented transformations, and that the idempotency and source-row tracking satisfy the auditability requirements.

Final decision:
Implemented the auditable remediation layer, explicit rule set, and dual-output (cleaned dataset + audit log) architecture as the official Phase 3 deliverable.

### Phase 3 Correction

AI contribution:
Identified that the current category normalization crossed the boundary from formatting normalization into unsupported semantic inference and that remediation counts were mixing action-level and record-level units.

My verification:
Reviewed the implementation and checked the remediation behavior against the Phase 2 evidence-first policy and generated outputs.

Final decision:
Restricted automatic category normalization to formatting-only cases and separated action-level audit metrics from record-level disposition metrics.

### Phase 4 Decision Analysis & Metric Definitions

AI contribution:
AI assisted in defining rigorous numerators, denominators, and eligibility logic for the organizer questions. It identified censorship bias in directly comparing average case durations and recommended the 30-day closure rate and median duration as unbiased indicators. It also correctly identified that Question 3 was unanswerable because the `priority` field was 100% missing in 2023, thus preventing the establishment of a pre-triage baseline.

My verification:
I reviewed the code implementation (`analyze.py`, `analysis_spec.py`), the mathematical formulations in the JSON/MD output, and executed tests verifying that the 126 temporal contradictions skipped during parsing were securely excluded during analysis. I validated that the data limitations identified for Q3 matched the actual missingness in the CSV.

Final decision:
Approved the analytical pipeline, established Weybridge as the driver of performance degradation, and definitively ruled Q3 unanswerable with the provided dataset.

### Phase 5 â€” Reproducible Evidence Reporting
**AI contribution:**
Designed the deterministic reporting architecture ( uild_reports.py) to trace final analytical conclusions back to raw anomaly and remediation outputs. Extracted required lineage constraints and enforced explicit cross-phase mathematical reconciliation. Implemented a robust testing layer checking immutability, determinism, and absence of causal language.
**My verification:**
Reviewed the generated Markdown reports for readability and tone. Verified the reconciliation logic manually (Raw Rows = Retained + Dropped). Checked that the deterministic execution produces the exact same output bytes upon repeated runs, free of absolute paths.
**Final decision:**
Approved the reporting layer to serve as the evaluator-facing evidence package, confirming it does not silently discard data or hallucinate results.

### Phase 6 - Adversarial Validation & System Hardening
**AI contribution:**
AI assisted in designing adversarial failure categories (schema, missingness, large-input, missing upstream files) and implementing isolated test suites using Pytest temporary directories. It identified unsafe behavior in  nalyze.py (empty DataFrame apply crash) and  uild_reports.py (hardcoded artifact path swallowing test failures).
**My verification:**
Verified the defects existed by running the adversarial test suite and confirming failures. Validated that the underlying fixes (gracefully checking df.empty and utilizing sys.argv[1] for output targets) correctly resolved the vulnerabilities without breaking the real data pipeline.
**Final decision:**
Approved the hardening modifications as they prevent loud failure from missing files and silent failure/crashes from extreme downstream filtering.

### Phase 7 - Final Reproducibility & Submission Gate
**AI contribution:**
AI assisted in performing a comprehensive repository and dependency audit. It identified that numpy was directly imported in the source code but only implicitly provided via pandas, introducing a reproducibility risk.
**My verification:**
Verified the import traces using grep and confirmed numpy was missing from requirements.txt. Validated the addition of numpy to the requirements file to ensure explicit tracking.
**Final decision:**
Approved the strict dependency management approach to guarantee portable environment construction.

### Phase 7 - Clean-Clone Reproducibility
**AI contribution:**
AI assisted in creating a clean-clone isolation test environment outside the repository. It executed the entire pipeline from a fresh clone, verified cross-phase mathematical reconciliation, verified SHA-256 integrity, and ensured deterministic execution without hidden environmental dependencies. It identified that python src/dirty_data/*.py executions failed due to Python's module path resolution and provided a minimal sys.path injection fix to make the repository fully portable.
**My verification:**
I observed the simulated fresh clone execution pass all regression tests (67/67). I verified that no absolute paths remained in the codebase and that the raw source data was immutable and byte-for-byte identical to the original.
**Final decision:**
Approved the pipeline as fully reproducible and isolated, and approved the path-injection fix to maximize evaluator portability without requiring heavy packaging setups.

## Phase S1 Part A â€” Source Contracts

**AI Contribution**
- Analyzed the Surprise Challenge source structure.
- Identified the schema differences between the original and supplementary datasets.
- Proposed separating the source contracts rather than weakening the original schema.
- Implemented the source-contract definitions and focused tests.

**My Contribution & Verification**
- Reviewed the proposed source-contract approach against the Surprise Challenge requirements.
- Confirmed that the original schema must remain strict and backward-compatible.
- Checked that the supplementary schema contains only fields actually present in the provided CSV.
- Reviewed the mapping assumptions before allowing implementation.
- Reviewed the resulting Git diff to ensure no adapter, reconciliation, analysis, or reporting logic was introduced prematurely.
- Confirmed that the original raw data remained unchanged.
- Confirmed that the existing regression tests remained passing before moving forward.

**Verification Evidence**
- Original tests: 67/67 passed.
- Total tests after S1 Part A: 71/71 passed.
- Original raw-file SHA-256 remained unchanged.
- No raw source files were modified.
- Commit: e55e246
- Push completed successfully.

**Decision**
Keep the original source contract strict and introduce a separate supplementary source contract.

**Why**
The two sources have different structures. Weakening the original contract would reduce the integrity of the original pipeline. Separate contracts allow the later adapter layer to explicitly transform each source into the canonical representation.

**Status**
S1 Part A completed and approved for the next phase.

### Phase S1 Part B — Canonical Model

**AI Contribution**
- Analyzed the semantic overlap between the original and supplementary sources.
- Designed the \CANONICAL_SCHEMA\ dict in \schema.py\ mapping business concepts (e.g., \district\ and \office\ to \canonical.district\).
- Explicitly designated \status\ as a derived field, \source_system\ as essential provenance metadata, and enabled \unavailable_allowed\ for fields like \contact_count\ to prevent fabricating zeros.
- Wrote \	est_canonical_schema_concepts\ and \	est_canonical_schema_properties\ to enforce that provenance, derived semantics, and missingness rules are structurally supported without dictating source precedence.

**My Contribution & Verification**
- Reviewed the canonical field definitions against the architecture requirements.
- Checked that missing source fields were not coerced to zero or default values in the schema.
- Confirmed that \status\ semantics were represented as conceptually derived.
- Reviewed the Git diff to ensure no adapters, reconciliation, or analysis logic were introduced.
- Checked the regression test results to guarantee original baseline behavior remained untouched.
- Decided the structural canonical model accurately fulfills the business concepts required for future Phase S6 reconciliation.

**Verification Evidence**
- All previous tests plus new tests passed: 73/73.
- Original raw CSV SHA-256 verified unchanged (f65bec45...).
- Commit: 81a384b
- Push completed successfully.

**Decision**
Establish a strict, distinct Canonical Schema that neutralizes vocabulary differences between the sources while preserving explicit null/unavailable states and supporting metadata tracking.


### Phase S2 Part A — Original Source Adapter

**AI Contribution**
- Implemented \dapt_original_to_canonical\ in \src/dirty_data/adapter.py\ to deterministically map the Original data to the Canonical Schema.
- Configured the adapter to preserve missingness by maintaining empty strings instead of imputing zeros for missing fields.
- Ensured the adapter retains the exact \status\ from the original dataset instead of blindly re-deriving it from malformed dates.
- Authored 4 focused adapter tests in \	ests/test_adapter.py\ verifying mappings, missing value preservation, malformed date pass-through, and determinism.

**My Contribution & Verification**
- Reviewed the original field mappings to ensure stable, 1:1 translation for existing fields.
- Checked the adapter against the CANONICAL_SCHEMA to confirm \source_system\ ('ORIGINAL') and \extract_date\ ('') were applied without fabrication.
- Verified that no supplementary data processing, merging, or identity matching was introduced in this phase.
- Confirmed missing values and malformed dates were accurately preserved without altering existing anomaly behaviors.
- Reviewed the diff and regression test results (77/77) to guarantee the frozen analysis baseline was not impacted.
- Decided the isolated adapter correctly fulfills S2 Part A boundaries without premature integration.

**Verification Evidence**
- Collected: 77 items
- Passed: 77
- Failed: 0
- Original raw CSV SHA-256 verified unchanged (f65bec45...).
- Commit: bbb246a
- Push completed successfully.

**Decision**
Adopt a standalone original source adapter that maps 1:1 into the Canonical Schema, maintaining missingness and source provenance without interfering with the existing operational pipeline.


### Phase S2 — Supplementary Source Adapter

**AI Contribution**
- Implemented \dapt_supplementary_to_canonical\ and \derive_supplementary_status\ in \src/dirty_data/adapter.py\.
- Ensured \contact_count\ and \client_ref\ were cleanly assigned empty strings to strictly enforce the unavailable-field distinction.
- Created 5 targeted tests for the supplementary adapter mapping logic, ensuring missing values, malformed dates, status derivation rules, and real dataset execution (4,180 rows) all passed.

**My Contribution & Verification**
- Reviewed field mappings to confirm reference correctly mapped to case_id and the other canonical names were utilized accurately.
- Checked the missingness handling to verify that no fabricated values were introduced (e.g., empty contact_count is not coerced to 0).
- Scrutinized the status-semantics derivation rule to ensure malformed or ambiguous dates refused to manufacture a false status certainty, aligning perfectly with the provided rule.
- Reviewed the codebase diff to verify no reconciliation logic, identity matching, deduplication, or dataset merging occurred.
- Audited the full regression suite (82/82 passing tests) and verified the original dataset raw SHA-256 hash remained pristine.
- Decided the Supplementary adapter fulfilled the requirements by isolating translation without impacting the Original processing pipeline.

**Verification Evidence**
- Test Count: 82 items collected.
- Test Results: 82 passed, 0 failed.
- Raw Hashes: Original CSV (f65bec45...) and Supplementary CSV (95ed4d9f...) verified immutable.
- Commit: 511c5b4
- Push completed successfully.

**Decision**
Adopt the isolated supplementary adapter function, establishing a purely structural translation layer for the supplementary data that safely preserves extraction dates, empty string omissions, and safely derived conceptual status without prematurely reconciling cross-source conflicts.


### Phase S3 — Identity Matching

**AI Contribution**
- Implemented \match_identities\ in \src/dirty_data/identity.py\ to establish cross-source equivalence without prematurely resolving conflicts.
- Utilized a flattened alignment dataframe approach (\pd.concat\ followed by deterministic sorting) to preserve all canonical properties and provenance metadata without risking the silent-drop dangers of \pd.merge\ or \drop_duplicates\.
- Added test coverage in \	ests/test_identity.py\ that validates dynamic overlap calculations (confirming the exact 14,916 orig / 4,180 supp / 3,400 overlap numbers) and strictly proves row conservation (19,280 total records).

**My Contribution & Verification**
- Reviewed the identity-matching alignment logic to verify no data cleaning or conflict resolution was hidden within the alignment step.
- Approved the concatenated output structure, ensuring it perfectly positions S4/S5 phases to use grouped case_id iterations.
- Validated regression tests to ensure previous Phase 0-7 architecture was completely unaffected.
- Verified all 84/84 tests passed and the exact overlap metrics matched the baseline expectations.

**Verification Evidence**
- Test Count: 84 items collected.
- Test Results: 84 passed, 0 failed.
- Row Conservation: Output contains exactly 19,280 rows (15,100 orig + 4,180 supp).
- Commit: db758b4
- Push completed successfully.

**Decision**
Adopt the concatenated identity ledger approach. Identity mapping is purely an association phase establishing multi-source groupings for future downstream comparison, fully maintaining the required non-destructive boundary.


### Phase S3 Correction — Explicit Identity Index

**AI Contribution**
- Modified \match_identities\ to generate \identity_index_df\, calculating the exact physical row count per unique \case_id\ across both sources.
- Implemented \_compute_match_status\ to assign \MATCHED\, \ORIGINAL_ONLY\, or \SUPPLEMENTARY_ONLY\.
- Implemented \_compute_cardinality\ to establish neutral relationship multiplicity (\ONE_TO_ONE\, \ONE_TO_MANY\, \MANY_TO_ONE\, \MANY_TO_MANY\, \ORIGINAL_ONLY\, \SUPPLEMENTARY_ONLY\) dynamically.
- Retained the untouched \ligned_df\ to preserve 100% of the physical records and provenances without deduplication.
- Wrote comprehensive regression tests verifying every cardinality type and explicitly proving physical duplicates in Original (like the 184 identified cases) are preserved in the ledger while properly tracked as \MANY_TO_ONE\ or \MANY_TO_MANY\ in the index.

**My Contribution & Verification**
- I reviewed the S3 read-only audit and identified that aggregate overlap metrics were insufficient for an auditable per-identity relationship artifact.
- I decided that S3 must expose both the physical identity ledger and an explicit identity index.
- I specifically required cardinality to describe multiplicity without triggering deduplication.
- I reviewed the proposed classification rules for MATCHED, ORIGINAL_ONLY, and SUPPLEMENTARY_ONLY.
- I checked that no source precedence or reconciliation logic was introduced.
- I reviewed the duplicate-identity test cases and confirmed that physical rows remain preserved.
- I reviewed the regression test results before allowing the phase to close.


### Phase S4 — Field-Level Comparison

**AI Contribution**
- Created \compare.py\ to execute deterministic Cartesian field-level comparisons for matching identities.
- Implemented comparison taxonomy logic distinguishing \EXACT_MATCH\, \REPRESENTATION_EQUIVALENT\, \CONFLICT\, \MISSING_ONE_SIDE\, \UNAVAILABLE_ONE_SIDE\, \INVALID_COMPARISON\, and \NOT_COMPARABLE\.
- Encoded \contact_count\ as explicitly unavailable for the Supplementary source to prevent fabricated 0s.
- Structured comparisons to retain verbatim source evidence and provenance (\source_row_index\) without resolving source precedence or deduplicating records.
- Wrote 20 tests guaranteeing no raw data modifications, strict missing vs. unavailable semantics, and no assumed winners.

**My Contribution & Verification**
- I reviewed the multi-record ambiguity identified during S4 planning.
- I explicitly approved Cartesian comparison as an exhaustive evidence-generation strategy.
- I verified that Cartesian combinations do not imply confirmed physical-record correspondence.
- I verified that no deduplication or source precedence was introduced.
- I reviewed the comparison artifact for provenance preservation.
- I reviewed the complete test suite.
- I verified raw-data integrity.

