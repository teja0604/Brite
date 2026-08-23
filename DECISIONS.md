# Engineering Decisions

## 1. Why Python Pipeline Instead of a Web App / Frontend / Database?

### Problem
The challenge requires cleaning dirty CSV data, reconciling sources, producing defensible analytical answers, and making the process reproducible.

### Alternatives Considered
- Python/pandas pipeline
- SQL/database pipeline
- Web application/dashboard
- Notebook-only solution
- Cloud/data-engineering stack

### Decision
Use a lightweight Python pipeline with pandas and explicit processing modules.

### Why This Choice
The dataset is small enough for in-memory processing. The core problem is deterministic data transformation and analysis, not serving users interactively.

The handbook explicitly allows a notebook as a valid delivery and states that a dashboard, web app, or interactive frontend is not required.

Therefore, adding React, FastAPI, PostgreSQL, Docker infrastructure, or cloud services would increase complexity without improving the required analytical outcome.

### Trade-off
A database or distributed framework would scale better to very large datasets, but that scalability is unnecessary for the provided dataset and would add deployment and reproducibility complexity.

---

## 2. Why Keep Raw CSV Immutable?

### Alternatives
- Edit the CSV directly
- Create a manually cleaned CSV
- Transform the data immediately during ingestion

### Decision
Treat the supplied CSV as immutable evidence.

### Why
The evaluator should be able to determine exactly what was provided and reproduce every transformation.

This also supports the handbook's requirement for transparent data-quality assessment rather than hiding dirty values before analysis.

### Trade-off
More intermediate artifacts and code are required, but provenance and reproducibility are significantly stronger.

---

## 3. Why Read Data as Strings Instead of Automatic pandas Types?

### Alternatives
- Let pandas infer types
- Automatically parse dates/numbers during ingestion
- Read everything as strings and explicitly interpret values later

### Decision
Read raw fields as strings and perform explicit interpretation later.

### Why
Automatic inference can change the representation of dirty data before we inspect it. This is particularly dangerous for ambiguous dates and identifiers.

Explicit interpretation keeps ingestion lossless and moves business meaning into controlled rules.

### Trade-off
More explicit parsing code is required, but the raw evidence is preserved.

---

## 4. Why Separate Detection From Remediation?

### Alternatives
- Clean everything in one script
- Detect anomalies and immediately modify values
- Separate detection and remediation

### Decision
Separate anomaly detection from cleaning.

### Why
Detection answers:

> "What is wrong with the data?"

Remediation answers:

> "What are we allowed to do about it?"

Combining both would make it difficult to distinguish observed problems from assumptions introduced by the cleaning process.

### Trade-off
The architecture has more stages, but every cleaning decision becomes auditable.

---

## 5. Why Explicit Date Rules Instead of pandas Date Inference?

### Alternatives
- `pd.to_datetime()` inference
- Locale-based parsing
- Explicit format rules

### Decision
Use explicit deterministic date rules.

### Why
Values such as `03/04/2024` can legitimately represent different dates depending on interpretation.

The system therefore refuses to guess. Canonical and explicitly unambiguous formats are converted; ambiguous or invalid dates remain flagged.

### Why Better
This produces defensible analytical eligibility instead of silently introducing a date assumption.

### Trade-off
More code and more test cases are required, but the result is auditable and deterministic.

---

## 6. Why Conservative Cleaning Instead of Aggressive Normalization?

### Alternatives
- Fuzzy matching
- Automatic category mapping
- `drop_duplicates()`
- `fillna()`
- Frequency-based canonicalization

### Decision
Only perform transformations supported by explicit evidence.

Examples:
- Formatting-only category differences may be normalized.
- Ambiguous dates are not guessed.
- Candidate identities are not automatically merged.
- Missing values are not blindly imputed.
- Exact duplicates can be removed with provenance.

### Why Better
Similarity does not prove semantic equivalence.

Aggressive cleaning can make the dataset look cleaner while actually creating incorrect business meaning.

### Trade-off
Some records remain unresolved, but the analytical results are more defensible.

---

## 7. Why Explicit Record-Level Eligibility?

### Alternatives
- Delete every problematic row
- Keep every row in every calculation
- Define eligibility separately for each analysis

### Decision
Keep records whenever possible but define whether each record is eligible for a particular analysis.

### Why
A case with a bad closure date may still be valid for case-count analysis even if it cannot safely be used for duration analysis.

This prevents unnecessary data loss.

### Trade-off
The pipeline becomes more complex because each analysis has explicit eligibility rules, but the denominator becomes transparent.

---

## 8. Why 30-Day Closure Rate Instead of Simple Average Duration?

### Alternatives
- Mean duration
- Median duration only
- 30-day closure rate
- Raw closure counts

### Decision
Use 30-day closure rate as the primary KPI and median duration as a secondary KPI.

### Why
Recent cases are right-censored: a case opened near the end of 2025 may not have had enough time to close.

A fixed 30-day observation window provides a more comparable measure across years.

### Trade-off
The metric does not describe the entire duration distribution, so median duration is retained as supporting evidence.

---

## 9. Why Refuse Unsupported Q3 Conclusions?

### Alternatives
- Estimate missing 2023 priority values
- Use 2024/2025 only and claim a historical improvement
- Assume missing priority means low priority
- State that the question cannot be answered

### Decision
Do not fabricate a 2023 high-priority baseline.

### Why
The original data does not provide the evidence required for a valid pre-triage comparison.

The correct analytical behavior is to report the limitation rather than manufacture a baseline.

### Trade-off
One question remains partially or fully unanswerable, but the conclusion is scientifically defensible.

---

# Surprise Challenge Engineering Decisions

## 10. Why Separate Original and Supplementary Source Contracts?

### Alternatives
- Modify the original schema
- Append the supplementary CSV directly
- Create source-specific contracts and map both into a canonical model

### Decision
Keep separate source contracts and introduce a shared canonical representation.

### Why
The supplementary dataset has a different schema and missing fields.

Changing the original contract would risk breaking the already validated pipeline.

The adapter approach isolates source-specific differences.

### Trade-off
There is additional mapping code, but the original pipeline remains stable and both sources remain traceable.

---

## 11. Why Canonical Model Before Reconciliation?

### Alternatives
- Merge raw CSVs directly
- Reconcile source-specific columns directly
- Map both sources into a canonical model first

### Decision
Canonicalize first, reconcile second.

### Why
Structural differences should be solved before business conflicts are evaluated.

This separates:
- source structure,
- identity,
- comparison,
- reconciliation,
- analysis.

### Trade-off
Additional architecture layers are introduced, but responsibilities remain clear and testable.

---

## 12. Why Identity Index Instead of a Simple DataFrame Merge?

### Alternatives
- `pd.merge()`
- Dictionary mapping
- Flat concatenation only
- Explicit identity index

### Decision
Maintain a physical identity ledger plus an explicit identity index.

### Why
A normal merge can hide one-to-many and many-to-many relationships and can create column duplication.

The identity index explicitly records cardinality without deciding which source is correct.

### Trade-off
More artifacts are produced, but identity relationships become auditable.

---

## 13. Why Compare Before Reconcile?

### Alternatives
- Choose a winning source immediately
- Merge values during identity matching
- Compare first, reconcile second

### Decision
Comparison produces evidence first; reconciliation applies approved rules afterward.

### Why
A conflict must be observed before a policy decides how to resolve it.

This prevents identity matching from accidentally becoming a business decision.

### Trade-off
More processing stages are required, but the source conflict remains visible.

---

## 14. Why Explicit Field-Level Precedence?

### Decision
Supplementary takes precedence only for `status` and `closure_date`; Original retains precedence for the other business fields.

### Why
The supplementary source represents an operational update, while the original source remains the baseline for the other attributes.

### Why Better
A field-specific rule is safer than saying "latest source always wins."

Different fields can have different business meanings and update behavior.

### Trade-off
The reconciliation policy is more detailed, but it avoids blanket source precedence.

---

## 15. Why Preserve MANY_TO_ONE Instead of Creating Synthetic Records?

### Alternatives
- Collapse all matching records into one
- Pick one source record
- Create a synthetic combined record
- Preserve physical records and report the population separately

### Decision
Preserve physical evidence and do not invent synthetic duration values.

### Why
Multiple physical records cannot safely be treated as one business event without additional evidence.

Synthetic records would create values that never existed in either source.

### Trade-off
Some records require separate analytical treatment, but no artificial data is created.

---

## 16. Why Keep Supplementary-Only Records Separate?

### Decision
Retain them and report them separately instead of automatically adding them to the primary analytical denominator.

### Why
They represent cases with no corresponding original baseline.

Including them directly could change year-over-year comparisons for reasons unrelated to the original population.

### Trade-off
The final reports contain multiple populations, but the analytical denominator remains transparent.

---

## 17. Why Independent Verification?

### Alternatives
- Unit tests only
- Integration tests only
- Re-run the same production calculation
- Independent verifier

### Decision
Use an independent verifier that reads frozen artifacts and recalculates key results separately.

### Why
If the verifier uses exactly the same logic as the production calculation, the same bug could exist in both places.

Independent calculation provides a stronger check.

### Trade-off
More development effort is required, but confidence in the final analytical artifacts is substantially higher.

---

## 18. Why Adversarial Testing?

### Alternatives
- Happy-path tests only
- Random testing only
- Explicit adversarial scenarios

### Decision
Test malformed schemas, missing artifacts, ambiguous dates, empty analytical populations, identity variants, corrupted outputs, and other boundary cases.

### Why
The pipeline is intended to be evaluated on correctness, not merely successful execution on the supplied happy path.

### Trade-off
Testing takes additional development time, but it exposes failures that normal examples would miss.

---

# Final Architecture Decision

The final architecture intentionally favors:

- Python + pandas over unnecessary application infrastructure.
- Explicit rules over implicit inference.
- Immutable evidence over destructive cleaning.
- Detection → remediation → analysis separation.
- Canonicalization → identity → comparison → reconciliation separation.
- Provenance over opaque transformations.
- Fixed-window metrics over biased recent-period averages.
- Explicit uncertainty over fabricated answers.
- Independent verification over trusting one calculation path.

The architecture is therefore not designed to be the most technologically complex solution.

It is designed to be the most appropriate solution for the provided problem, dataset, handbook requirements, reproducibility needs, auditability requirements, and Surprise Challenge.
