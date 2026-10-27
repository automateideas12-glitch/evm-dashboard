# EVM Dashboard — CE 725 Construction Economics and Finance

An interactive Earned Value Management (EVM) decision-support dashboard for construction projects (course Topic 7). It calculates PV, EV, AC, CV, SV, CPI, SPI, EAC (four selectable methods), ETC, VAC, forecast overrun and TCPI over multiple reporting periods, shows trend charts, screens project health against configurable thresholds and writes plain-language commentary. Every calculation is validated against an independent manual benchmark.

**Team:** Prashant Kumar (Project Lead & Finance Modeller) · Varun Chandak (Data Lead) · Sobhith R (AI & Tool Developer) · Arjun Andhare (Validation Engineer) · Shreyansh Singh (Documentation & Reflection Lead)

## Quick start

Requires Python 3.10 or later (tested on 3.13).

```bash
cd evm_dashboard
python -m pip install -r requirements.txt
streamlit run app.py
```

**Hosted version (Streamlit Community Cloud):** deploy this repository with main file `streamlit_app.py` (it simply runs `app.py`). Data uploaded to the hosted version is processed on Streamlit's servers, so use synthetic or non-confidential data there.

The browser opens at <http://localhost:8501> on a **home screen**: upload a CSV/XLSX, enter data manually, or open an example project in one click. Uploads go through a **smart reader** (rule-based, offline) that finds the header row, reads a status date written above the table, matches columns by meaning, detects the data type, removes total rows and converts fractions/lakh/crore — every change is listed on screen, and anything missing (e.g. actual cost) can be typed in the app. The full analysis (Overview, Trends, Forecasts, Commentary, Data) opens once a project is loaded; the sidebar's **Home** button returns to the start. No internet connection or AI service is needed for any calculation.

## Run the checks

```bash
python -m pytest                                  # 79 automated tests
python benchmark/independent_benchmark_calc.py    # regenerate the independent expected values
python benchmark/compare_with_dashboard.py        # regenerate the manual-vs-dashboard table
```

## Folder guide

| Path | Contents |
|---|---|
| `app.py` | Streamlit interface only (no formulas) |
| `src/metric.py` | Result type carrying value + status (ok / review / undefined / not applicable) |
| `src/evm_calculations.py` | CV, SV, CPI, SPI, % of BAC; applies everything per reporting date |
| `src/forecasting.py` | EAC methods A–D, ETC, VAC, overrun, TCPI to BAC and to EAC |
| `src/data_processing.py` | File reading, column mapping, PV/EV/AC derivation for the three input modes |
| `src/validation.py` | Parsing and validation rules (errors / warnings / info) |
| `src/commentary.py` | Health screening and rule-based commentary |
| `src/charts.py`, `src/formatting.py` | Charts and display formatting (display-only rounding) |
| `tests/` | pytest suite; `browser_test_playwright.py` is the real-browser check (run manually) |
| `benchmark/` | Independent benchmark: exact-fraction script, plain-formula workbook, expected values |
| `data/` | Synthetic sample datasets and the benchmark case |
| `templates/` | Blank input templates for each input mode |
| `documentation/` | Charter, RTM, formula reference, data dictionary, assumptions & limitations |
| `reports/` | User manual, validation report, AI usage log, reflection draft, presentation outline, viva bank, test evidence, screenshots |
| `PROJECT_STATUS.md` | Current status, decisions, open items |

## Important limitations (full list in `documentation/assumptions_and_limitations.md`)

- Forecasts are assumption-based estimates, never guarantees.
- Health thresholds are team-chosen screening rules, not industry standards.
- SPI is a budget-value measure; it does not show critical-path delay and tends to 1.00 at completion even for late projects.
- One baseline per dataset (no re-baselining); one currency per project.
- All bundled data is synthetic and illustrative.
