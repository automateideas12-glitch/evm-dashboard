# Assumptions and limitations

Category: **A** = required by the course guidelines; **B** = engineering assumption adopted by the team; **C** = optional enhancement. "How to change" says where a user or developer can alter the assumption.

## Assumptions

| # | Assumption | Cat. | How to change |
|---|---|---|---|
| A1 | All inputs are cumulative to the status date unless the column is explicitly a period column (`ac_period`). | B | Use the documented columns. |
| A2 | If both cumulative and period AC are supplied, cumulative AC is used; period AC is only used to check consistency. | B | Code: `_ac_series` in `src/data_processing.py`. |
| A3 | If only period AC is supplied, cumulative AC is the running total, assuming the first row is the first period since project start and no period is missing. | B | Supply cumulative AC instead. |
| A4 | Actual progress % measures the share of **budgeted scope** physically complete. | B | Not checkable by software; a measurement responsibility of the user. |
| A5 | One approved baseline (BAC and WP budgets constant) per dataset. | B | Analyse each baseline as a separate dataset. |
| A6 | Default forecast method is A (BAC/CPI) because it is the simplest widely taught method; it is **not** presented as the best. | B | Sidebar selector. |
| A7 | Health thresholds (CPI/SPI 1.00/0.90; overrun 0%/10%; TCPI gap 0.10) are screening rules chosen by the team. | B | Sidebar → Health screening thresholds. |
| A8 | Review flags at < 10% complete and EAC > 3 × BAC. | B | Constants in `src/forecasting.py`. |
| A9 | Non-ISO dates are read day-first (DD/MM/YYYY), the common convention in India. | B | Setting in the Data tab. |
| A10 | Money difference below ₹0.50 is treated as rounding when checking consistency (e.g. cumulative vs period AC). | B | `MONEY_TOL` in `src/validation.py`. |
| A11 | Commentary is rule-based and offline (the guideline lists AI-written commentary as a role of AI; the brief requires offline core operation). | B | `src/commentary.py`. |

## Known limitations

1. **Forecasts are not predictions of certainty.** Each EAC holds only under its stated assumption.
2. **SPI is not a schedule-delay measure.** It is budget-weighted, ignores the critical path and tends to 1.00 as work completes even if the project finishes late. Earned Schedule (time-based SPI) is not implemented.
3. **Percentage inputs lose precision when rounded.** Example found during testing: the progress-based demo file stores percentages to 6 decimals; EV for 31-Aug-2026 differs by ₹0.40 (on a ₹12 crore BAC) from the work-package source data. Prefer pre-calculated or work-package input when exact reconciliation matters.
4. **No re-baselining, change orders or contingency/management-reserve tracking.**
5. **One currency per project**; no escalation or currency conversion.
6. **Work-package mode needs every WP at every date** and per-WP cumulative AC; costs not allocated to a WP can be entered as a zero-budget WP.
7. **Session-only state.** Manual edits and independent ETC entries exist until the browser session ends; export the workbook to keep them.
8. **Cell editing in the manual-entry table was not verified by automated browser test** (the canvas-based grid did not accept scripted edits). Loading a manual table and the shared validation path are verified. See validation report §11.
9. **Single-user local app.** No authentication; do not expose it on a shared network with confidential data.
10. **Synthetic data only.** No real project has been used to validate practical usefulness; practitioner testing is recommended (bonus criterion).

## Data handling, confidentiality and privacy

- The app runs locally; uploaded files are processed in memory on the machine running Streamlit and are not sent anywhere by the app. (Streamlit's usage statistics are disabled in `.streamlit/config.toml`.)
- The Google Fonts stylesheet is requested by the browser for typography only; no project data is included. Offline, the app falls back to system fonts.
- Do not paste real client data into public AI tools when extending or debugging the tool; use the synthetic datasets.
