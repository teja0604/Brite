# Problem 2 — Dirty Data, Real Decisions
## Data pack

### Contents

| File | What it is |
|:--|:--|
| `case-export-2023-2025.csv` | The export from the case management system. 15,100 rows. |
| `questions.md` | The three questions the program director wants answered. |

### The export

One CSV, ten columns, covering cases with an intake date between 1 January 2023 and 31 December 2025.

| Column | Meaning |
|:--|:--|
| `case_id` | The case reference as recorded in the source system. |
| `client_ref` | Client name as recorded. Synthetic. |
| `district` | One of four district offices: Calder Central, Northgate, Weybridge, Ash Hill. |
| `intake_date` | When the case was opened. |
| `closure_date` | When the case was closed. Empty where the case is still open. |
| `status` | `Open` or `Closed`. |
| `category` | The case type. |
| `priority` | Priority band, where recorded. |
| `caseworker_id` | The assigned caseworker. |
| `contact_count` | Number of recorded contacts on the case. |

### What you should know before you start

This export came out of a system that has been in place for years, through at least one migration, maintained by a changing group of people with no strong convention about how anything should be entered. It shows.

You should expect to find, among other things:

- The same case appearing more than once under identifiers that differ in punctuation, spacing, or case.
- More than one date format inside a single column.
- Records that are internally contradictory in ways that are physically impossible.
- A category column of which roughly a third is uncontrolled free text.

That list is not exhaustive, it does not tell you how much of each there is, and it does not tell you which of these actually matters for the three questions. Those are the parts worth your time.

One piece of advice, offered because it is where this problem is usually lost: **be careful about what you drop silently.** A parser that skips rows it cannot read will produce a clean-looking answer built on whatever happened to survive, and it will not tell you it did that.

### Reminder

A change to the requirements lands on day two. You will not be told what it is.
