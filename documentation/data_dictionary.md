# Data dictionary

Column names below are the standard template headers (`templates/`). Other names are recognised automatically where listed in `SYNONYMS` (`src/data_processing.py`) — e.g. `BCWS` → PV, `BCWP` → EV, `ACWP` → AC — and every suggestion is shown for confirmation before use. Unrecognised columns are ignored, never guessed.

**Type** C = cumulative to the reporting date · P = this reporting period only · K = constant for the project · T = text.

| Column | Meaning | Type | Unit / format | Required in |
|---|---|---|---|---|
| `reporting_date` | Status date the values refer to | — | YYYY-MM-DD (other formats read as DD/MM/YYYY by default, switchable) | all modes |
| `planned_progress_pct` | Baseline share of budgeted scope planned to be complete | C | % 0–100 (a trailing `%` is accepted) | progress, work package |
| `actual_progress_pct` | Share of budgeted scope **physically** complete (quantities, milestones) — not time elapsed, not duration % | C | % 0–100 | progress, work package |
| `pv_cumulative` | Planned Value | C | currency | precalc |
| `ev_cumulative` | Earned Value | C | currency | precalc |
| `ac_cumulative` | Actual Cost | C | currency, ≥ 0 | progress/precalc: this **or** `ac_period`; work package: required per WP |
| `ac_period` | Cost incurred in this period only | P | currency | alternative to `ac_cumulative`; summed only if no cumulative AC |
| `bac` | Budget at Completion | K | currency, > 0 | progress/precalc (column or settings) |
| `independent_etc` | Bottom-up estimate of remaining cost (method D) | C (as at date) | currency, ≥ 0 | optional |
| `activity_id` | Work-package identifier | T | — | work package |
| `activity_name` | Work-package description | T | — | optional |
| `activity_budget` | Approved budget of the work package | K | currency, ≥ 0 | work package |
| `notes` | Explanation (shown in commentary as a user note) | T | — | optional |
| `project_name`, `currency` | Project constants | K | — | optional (settings otherwise) |

Money accepts thousands separators (Indian or Western), currency symbols (₹, $, €, £, INR, Rs) and accounting negatives such as `(1,000)`. Blank cells are **missing**, never zero.

## Output columns (Results CSV / Excel "EVM results" sheet)

For each metric `X` there are columns `X` (value; blank = no value) and `X__status` (`ok`, `review`, `undefined`, `not_applicable`). The workbook also includes `X__note` with the reason. Metric keys: `bac, pv, ev, ac, cv, sv, cpi, spi, pct_planned, pct_complete, pct_spent, tcpi_bac`, and for each method `A_CPI, B_CPI_SPI, C_BUDGET_RATE, D_INDEPENDENT`: `eac_*, etc_*, vac_*, overrun_*, overrun_pct_*, tcpi_eac_*`.
