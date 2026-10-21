# PROJECT_STATUS — CE 725 EVM Dashboard

_Last updated: 21-Oct-2026. Final submission due 1-Nov-2026._

## Objective
Interactive, validated Earned Value Management decision-support dashboard for construction projects (Topic 7), with all course deliverables.

## Mandatory requirements (course PDF)
Working tool + source · user manual (3–5 pp) · validation report with manual benchmark for two periods · AI usage log (≥ 20 entries, Annexure A) · reflection report (10–15 pp, 6 sections) · 15-min presentation + demo + viva. Full list with status: `documentation/requirements_traceability_matrix.md`.

## Current status

| Area | Status | Evidence |
|---|---|---|
| Calculation engine (all Topic 7 metrics, 4 EAC methods, both TCPIs) | Tested and passed | `reports/test_results.txt` (79 passed) |
| Benchmark, two periods | 162/162 comparisons pass (3 input modes) | `reports/benchmark_comparison.md` |
| Input: CSV/XLSX upload, mapping, validation, manual entry, 3 modes | Tested and passed (manual cell edit: see open item 3) | tests + `reports/browser_test_log.txt` |
| Dashboard: 5 tabs, charts, commentary, exports | Tested (AppTest + browser) | `tests/test_app.py`, screenshots |
| User manual | Done, 5 pages | `reports/user_manual.pdf` |
| Validation report | Done; team sign-off pending | `reports/validation_report.pdf` |
| AI usage log | 21 genuine entries from the build session; team confirmation pending | `reports/ai_usage_log.csv` |
| Reflection report | Draft; individual sections to be written by members | `reports/reflection_report_draft.md` |
| Presentation | Outline + viva bank; slides not built | `reports/presentation_outline.md`, `reports/viva_question_bank.md` |

## Tests executed (21-Oct-2026)
- `python -m pytest`: 79 passed (Python 3.13; Streamlit 1.66, pandas 3.0.5) and 79 passed (Streamlit 1.50, pandas 2.2.3, Plotly 5.24).
- Mutation testing: 7/7 injected formula errors detected.
- Browser (Chromium/Playwright, `tests/browser_test_playwright.py`): all tabs render; invalid upload blocked with row-level errors and project unchanged; valid CSV upload loads; manual entry reproduces benchmark P2 (CPI 0.917, SPI 0.846, EAC(A) ₹436.36 lakh, TCPI 1.077).

## Defects found and fixed
D1 test matched a docstring · D2 project name carried across uploads · D3 duplicate error for one cell · D4 internal field name in a warning · D6 layout issues. D5 (₹0.40 precision from rounded %) documented as a limitation. Details: validation report §7.

## Open items — require team action
1. **Paper re-check of the benchmark** by the Validation Engineer and sign-off (validation report §15).
2. **AI usage log:** confirm decisions; add genuine earlier entries (topic choice, charter, any other AI use).
3. **Manual-table cell edit**: 2-minute hands-on check (change an AC to −5 → blocking error expected).
4. **Individual reflections** (half page each) and team edits to the reflection draft.
5. **Slides** from the outline; rehearse the demo and viva.
6. **Confirm** Validation Engineer's surname (charter "Andhare" vs brief "Bhadare") and the team number.
7. Optional bonus: practitioner test and documented feedback.

## Decisions and assumptions
See `documentation/assumptions_and_limitations.md` (A1–A11). Key: cumulative inputs; cumulative AC wins over period AC; health thresholds 1.00/0.90 and 0%/10% are screening rules; default method A is not presented as best; commentary is rule-based/offline.

## Known limitations
Forecasts are assumption-based; SPI not a time measure (no Earned Schedule); no re-baselining or change orders; one currency; session-only state; synthetic data only.

## Next actions
Team: open items 1–6. Optional development: Earned Schedule, re-baselining, persisted projects, slide deck.
