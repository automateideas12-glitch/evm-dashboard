# Requirements Traceability Matrix (RTM)

Source codes: **CP** = Course Project PDF (section), **CH** = team charter, **TB** = team development brief (section). Category: **A** = explicitly required by the professor, **B** = reasonable engineering assumption/requirement adopted by the team, **C** = optional industry-oriented enhancement.

Statuses: Not started · In progress · Implemented, not tested · Tested and passed · Blocked · **Awaiting team** (cannot be completed by the tool developer alone — needs genuine team input).

_Last updated: 2026-10-29 (see PROJECT_STATUS.md for the change log)._

| # | Requirement | Cat. | Source | Implementation | Verification method | Status |
|---|---|---|---|---|---|---|
| R1 | Compute PV, EV, AC | A | CP §5.2 Topic 7 | `src/data_processing.py` (derivation), `src/evm_calculations.py` | Benchmark comparison; unit tests | Tested and passed |
| R2 | Compute CPI, SPI | A | CP Topic 7 | `src/evm_calculations.py` | Benchmark; unit tests incl. zero denominators | Tested and passed |
| R3 | Compute EAC, ETC | A | CP Topic 7 | `src/forecasting.py` (methods A–D) | Benchmark (A, B, C); unit tests (A–D, invalid cases) | Tested and passed |
| R4 | Compute TCPI | A | CP Topic 7 | `src/forecasting.py` (TCPI to BAC and to EAC, separately labelled) | Benchmark; unit tests incl. infeasible BAC | Tested and passed |
| R5 | Trend charts | A | CP Topic 7 | `app.py` Trends tab (PV/EV/AC, CPI, SPI, progress, BAC vs EAC) | App test run + screenshots | Tested and passed (interface tests + screenshots) |
| R6 | Takes planned vs actual progress and cost data | A | CP Topic 7 | Three input modes; CSV/XLSX upload; manual entry | Unit tests; app test | Tested and passed |
| R7 | Validate: manually compute all EVM indices for two reporting periods | A | CP Topic 7 | Part A: `benchmark/` (paper working, exact-fraction script, plain-formula workbook), `tests/test_benchmark.py`. Part B (real data): `data/manual_check/IJzertoren_manual_check_workbook.xlsx`, `tests/test_manual_check_case.py`, `benchmark/compare_manual_check_case.py` | Comparison tables in validation report §6 and §6B | Tested and passed (162/162 and 90/90) — **Awaiting team** paper re-check (validation report §15) |
| R8 | Plain-language monthly progress commentary | A | CP Topic 7 ("Role of AI") | `src/commentary.py` — rule-based, offline (see note N1) | Unit tests; app test | Tested and passed (rule-based; see N1) |
| R9 | Working tool + all source files | A | CP §6.1 | GitHub repository `evm-dashboard` (deployed on Streamlit Community Cloud from `main`), `requirements.txt`, README | Launch from documented command | Tested and passed (launched with documented command) |
| R10 | User manual (3–5 pages) | A | CP §6.2 | `reports/user_manual.md` | Review against implemented features | Implemented (5 pages); team review |
| R11 | Validation report (benchmark, discrepancy table, resolution) | A | CP §6.3 | `reports/validation_report.md` | Generated from actual test run | Implemented from actual runs; team sign-off pending |
| R12 | AI usage log, ≥ 20 significant entries, Annexure A format | A | CP §6.4, Annex A | `reports/ai_usage_log.csv` / `.xlsx` | Entry count; team review | In progress — 37 genuine entries (21–29 Oct); **Awaiting team** confirmation of decisions and team entries |
| R13 | Learnings & reflection report, 10–15 pp, 6 sections | A | CP §6.5, §7 | `reports/reflection_report_draft.md` / `.docx` / `.pdf` | Section checklist; page count | In progress — draft with all 6 sections, 10 pages before individual reflections; **Awaiting team** (individual reflections must be written by each member; team rewrite) |
| R14 | 15-min presentation + live demo; any member can explain any formula | A | CP §6.6, §8.1 | 16-slide deck with speaker notes (Slides artifact), `reports/presentation_outline.md` (timing, demo script), `reports/viva_question_bank.md` (44 Q&A), `data/demo_files/` | Rehearsal by team | Implemented — **Awaiting team** rehearsal and speaker assignment |
| R15 | Every number verified against a manual benchmark | A | CP §1.2 | Two benchmarks (synthetic and real) + tests | Comparison tables, zero unexplained discrepancies | Tested and passed (benchmark scope); **Awaiting team** paper verification |
| R16 | Record every AI error found | A | CP §2 (Validation Engineer) | Validation report §7, AI log | Review | Tested and passed (validation report §7, AI log) |
| R17 | Reflect on confidentiality, privacy, data security | A | CP §3 | Reflection report §6; assumptions doc | Review | Implemented (assumptions doc, reflection §6); team to confirm policy |
| R18 | Project charter (Annexure B) | A | CP §4, Annex B | `documentation/project_charter.md` | Review | Implemented; team number and surname spelling to confirm |
| R19 | Undefined indices never shown as 0 | B | TB §7 | `Metric` status model | Unit tests | Tested and passed |
| R20 | Cumulative vs period distinction; never add cumulative values | B | TB §8 | `src/data_processing.py` | Unit tests | Tested and passed |
| R21 | Input validation (blocking vs warning), no silent repair/deletion | B | TB §9 | `src/validation.py` | Unit tests | Tested and passed |
| R22 | CSV + Excel upload, template, sample download, preview, column mapping, confirm before replace | B | TB rev. §7.1, §9.1 | `app.py` Data tab, `src/data_processing.py` | Unit + app tests | Tested and passed (browser: CSV upload; Excel via unit test) |
| R23 | Manual entry using same engine and validation | B | TB rev. §7.2 | `app.py` Data tab (editable tables) | App test; equivalence test | Tested and passed except browser cell-edit (not verified by automation — manual check pending) |
| R24 | Work-package-level (budget-weighted) EV | C | TB rev. §8.3 | `src/data_processing.py` | Benchmark (it is a WP case) | Tested and passed |
| R25 | Configurable health thresholds; "insufficient data" state | B | TB §12 | `src/commentary.py`, sidebar | Unit tests | Tested and passed |
| R26 | Export processed results | B | TB §10 | `app.py` downloads | App test | Tested and passed (unit export roundtrip; download buttons render) |
| R27 | Bonus: practitioner testing and feedback | C | CP §8.1 | Question list in reflection report §4; placeholder on slide 14 | Team activity | Not started — team activity |
| R28 | Smart reading of real site files (header row, status date, fractions, lakh/crore, totals, PV/EV cross-check) | B | Team request 27-Oct | `src/smart_reader.py` | `tests/test_smart_reader.py`; `tests/browser_smart_reader.py` (13/13) | Tested and passed |
| R29 | Home screen; always-visible Home, reporting date and method; combined CPI/SPI chart; work-package status; top problem activities | B | Team request 27/29-Oct | `app.py`, `src/analysis.py`, `src/charts.py` | `tests/test_app.py`, `tests/test_analysis.py`, `tests/test_charts.py`; screenshots | Tested and passed |
| R30 | Real-data case small enough to check by hand, showing every feature | B | Team request 29-Oct | `tools/build_manual_check_case.py`, `data/real/C2015-33_ijzertoren_manual_check_work_packages.csv`, workbook | `tests/test_manual_check_case.py` (incl. agreement with ProTrack values) | Tested and passed |

**N1.** The guideline lists "automatic plain-language monthly progress commentary" under the *Role of AI*. The brief requires the core tool to work offline without an LLM, so the dashboard's commentary is generated by transparent rules from the calculated metrics. The team should state this choice in the presentation; an optional LLM-written narrative could be added later with the confidentiality caveats in the reflection report.
