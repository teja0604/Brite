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
