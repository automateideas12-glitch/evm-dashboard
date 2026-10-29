# PROJECT_STATUS — CE 725 EVM Dashboard

_Last updated: 29-Oct-2026. Final submission due 1-Nov-2026._

## Objective
Interactive, validated Earned Value Management decision-support dashboard for construction projects (Topic 7), with all course deliverables.

## Mandatory requirements (course PDF)
Working tool + source · user manual (3–5 pp) · validation report with manual benchmark for two periods · AI usage log (≥ 20 entries, Annexure A) · reflection report (10–15 pp, 6 sections) · 15-min presentation + demo + viva. Full list with status: `documentation/requirements_traceability_matrix.md`.

## Current status

| Area | Status | Evidence |
|---|---|---|
| Calculation engine (all Topic 7 metrics, 4 EAC methods, both TCPIs) | Tested and passed | `reports/test_results.txt` (164 passed) |
| Benchmark A (synthetic), two periods | 162/162 comparisons pass (3 input modes) | `reports/benchmark_comparison.md` |
| Benchmark B (real: manual check case, DSLIB C2015-33, 4 WPs, 5 reports) | 90/90 workbook-vs-dashboard values pass; every WP at every date | `reports/manual_check_comparison.md`, `data/manual_check/IJzertoren_manual_check_workbook.xlsx` |
| Forecast test on real data at 50 % complete (C2014-05) | Dashboard = answer key; forecast errors recorded | `tests/test_forecast_at_50pct.py` |
| Input: smart reader, CSV/XLSX upload, validation, manual entry, 3 modes | Tested and passed (manual cell edit: see open item 3) | tests + `reports/browser_smart_reader_log.txt`, `reports/browser_test_log.txt` |
| Interface: home screen, top bar (date, method, Home), health banner, 5 tabs, combined CPI–SPI chart, WP status, top problems, commentary, exports | Tested (AppTest + browser) | `tests/test_app.py`, `tests/test_charts.py`, screenshots |
| User manual | Done, 5 pages | `reports/user_manual.pdf` / `.docx` |
| Validation report | Done (Parts A and B, D1–D16); team paper check and sign-off pending | `reports/validation_report.pdf` / `.docx` |
| AI usage log | 37 genuine entries (21–29 Oct); team confirmation and team entries pending | `reports/ai_usage_log.csv` / `.xlsx` |
| Reflection report | Draft, 10 pages with 6 sections; individual reflections to be written by members | `reports/reflection_report_draft.pdf` / `.docx` |
| Presentation | 16-slide deck with speaker notes (Slides artifact); outline with demo script; viva bank (44 Q&A) | `reports/presentation_outline.md`, `reports/viva_question_bank.md` |

## Tests executed (29-Oct-2026)
- `python -m pytest`: 164 passed (Python 3.13; Streamlit 1.66, pandas 3.0.5). Earlier: 79 passed on Streamlit 1.50 / pandas 2.2.3 / Plotly 5.24 (21-Oct).
- Mutation testing: 7/7 formula errors (21-Oct), 7/7 home-screen/analysis, 10/10 smart reader, 3/3 PV/EV cross-check (27-Oct), 6/6 charts/top bar/manual case (29-Oct).
- Browser (Chromium/Playwright): `tests/browser_test_playwright.py` (all tabs, invalid upload blocked, manual entry reproduces benchmark P2) and `tests/browser_smart_reader.py` (13/13 checks on the team's site sheet).

## Change log
- 29-Oct-2026: manual check case (real data, 4 work packages, hand-calculation workbook with 502 formulas; 90/90 values match); always-visible top bar (reporting date, forecasting method, ← Home); refined banner, cards and charts (one label per date, CPI/SPI zones, single-date note); 50 %-complete forecast test on real data; deliverables updated (user manual, validation report Part B and D7–D16, AI log 37 entries, reflection draft 10 pp, viva bank, 16-slide deck, demo files in `data/demo_files/`).
- 27-Oct-2026: supplied PV/EV columns are cross-checked row by row against budget × progress % instead of being flagged as unused (tested on Prashant's synthetic site sheet; 3/3 injected faults detected).
- 27-Oct-2026: smart reader for uploads (`src/smart_reader.py`, `tests/test_smart_reader.py`, `tests/browser_smart_reader.py`): finds header row, status date above table, matches columns by header + values with confidence, detects data type, removes total rows, converts fractions and lakh/crore, lets users supply missing actual cost; validation rows refer to the original spreadsheet. Tested on the team's own site sheet; 10/10 injected faults detected; browser test 13/13 checks pass (`reports/browser_smart_reader_log.txt`).
- 27-Oct-2026: home screen before analysis; combined CPI and SPI chart (Overview + Trends); work-package status and top problem activities panel (`src/analysis.py`, `tests/test_analysis.py`). 7/7 injected faults in the new code detected by tests.

## Defects found and fixed
D1 test matched a docstring · D2 project name carried across uploads · D3 duplicate error for one cell · D4 internal field name in a warning · D6 layout issues · D7 site sheet unreadable (header row, status date, fractions, totals) · D8 wrong row numbers · D9 supplied PV/EV flagged as unused · D10 one-date charts · D11 controls hidden in sidebar · D12 AI rounding slip (0.714 vs 0.713) · D13 guessed tolerance · D14 CSS for a non-existent element · D15 browser typing speed · D16 one-date note covering chart labels. D5 (₹0.40 precision from rounded %) documented as a limitation. Details: validation report §7.

## Open items — require team action
1. **Paper re-check** of both benchmarks (Part A and the manual check case) by the Validation Engineer and sign-off (validation report §15).
2. **AI usage log:** confirm each decision; add genuine team entries (topic choice, charter, any other AI tool used).
3. **Manual-table cell edit:** 2-minute hands-on check (change an AC to −5 → blocking error expected).
4. **Reflection report:** each member writes their half page (Section 5); the team rewrites Sections 1–4 and 6 in its own words and fills the bracketed items; check references.
5. **Presentation:** share the deck with the team, assign speakers, rehearse the 5-minute demo twice (script in `reports/presentation_outline.md`).
6. **Confirm** the Validation Engineer's surname (charter "Andhare" vs brief "Bhadare") and the team number.
7. Optional bonus: practitioner test and documented feedback (questions in reflection report §4).

## Decisions and assumptions
See `documentation/assumptions_and_limitations.md` (A1–A11). Key: cumulative inputs; cumulative AC wins over period AC; health thresholds 1.00/0.90 and 0%/10% are screening rules; default method A is not presented as best; commentary is rule-based/offline.

## Known limitations
Forecasts are assumption-based (real-data check: errors up to +93 % at mid-project for method B); SPI not a time measure (no Earned Schedule); no re-baselining or change orders; one currency; session-only state; smart reader handles common layouts only.

## Next actions
Team: open items 1–6. Optional development: Earned Schedule, re-baselining, persisted projects.
