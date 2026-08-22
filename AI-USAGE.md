# AI Usage Log

This document records meaningful AI-assisted engineering work. AI was used as an engineering support tool for analysis and review. I retained responsibility for the final engineering decisions and checked recommendations against the organizer material and actual project state.

## Phase 0 — Requirements and Architecture Review

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
