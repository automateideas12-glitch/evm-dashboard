# Formula reference

All values are **cumulative** to the reporting (status) date and in one currency. Calculations use full precision; rounding is applied only when values are displayed. Code location in brackets.

## Inputs and derivation (`src/data_processing.py`)

| Quantity | Progress-based mode | Pre-calculated mode | Work-package mode |
|---|---|---|---|
| BAC | entered / `bac` column | entered / `bac` column | Σ budgetᵢ |
| PV | planned % × BAC | supplied | Σ budgetᵢ × planned %ᵢ |
| EV | actual physical % × BAC | supplied | Σ budgetᵢ × actual %ᵢ |
| AC | cumulative AC supplied; else running total of period AC | same | Σ cumulative ACᵢ |

Work-package EV is **budget-weighted**. An unweighted average of work-package percentages is wrong: in the benchmark (Period 2) the simple average of 100%, 55%, 5%, 5% is 41.25%, giving EV = ₹1,65,00,000, whereas the budget-weighted EV is ₹1,76,00,000 (44%).

## Performance measures (`src/evm_calculations.py`)

| Metric | Formula | Reading | Undefined when |
|---|---|---|---|
| CV | EV − AC | > 0 favourable | an input is missing |
| SV | EV − PV | > 0 favourable; **money, not days** | an input is missing |
| CPI | EV ÷ AC | > 1 favourable | AC = 0 or AC < 0 |
| SPI | EV ÷ PV | > 1 favourable | PV = 0 or PV < 0 |
| % planned / earned / spent | PV, EV, AC ÷ BAC × 100 | — | BAC ≤ 0 |

## Forecasts (`src/forecasting.py`)

| Method | EAC formula | Assumption | Undefined when |
|---|---|---|---|
| A | BAC ÷ CPI | Cost efficiency to date continues | CPI undefined or 0 (EV = 0) |
| B | AC + (BAC − EV) ÷ (CPI × SPI) | Remaining work at CPI × SPI efficiency | CPI or SPI undefined, or product 0 |
| C | AC + (BAC − EV) | Remaining work at budgeted rate | input missing |
| D | AC + ETC(user) | Bottom-up re-estimate | no ETC supplied (not applicable) or ETC < 0 |

| Derived | Formula | Notes |
|---|---|---|
| ETC | EAC − AC | Negative ETC is kept and flagged *review*, never set to 0 |
| VAC | BAC − EAC | Negative = forecast over budget |
| Forecast overrun | EAC − BAC (= −VAC) | A forecast, distinct from AC > BAC (overrun already incurred) |
| Forecast overrun % | (EAC − BAC) ÷ BAC × 100 | BAC must be > 0 |
| TCPI to BAC | (BAC − EV) ÷ (BAC − AC) | Undefined if AC ≥ BAC with work remaining (BAC no longer achievable); not applicable if EV = BAC |
| TCPI to EAC | (BAC − EV) ÷ (EAC − AC) | Labelled separately from TCPI to BAC |

**Review flags** (value shown with ⚠): index-based EAC when < 10% of the work is earned; any EAC > 3 × BAC; negative ETC. These are team screening rules.

**Identities useful for checking:** TCPI to the method-A EAC = CPI; TCPI to the method-C EAC = 1; TCPI to the method-B EAC = CPI × SPI.

## Health screening (`src/commentary.py`, defaults; all configurable in the sidebar)

| Indicator | Warning | Critical |
|---|---|---|
| CPI, SPI | < 1.00 | < 0.90 |
| Forecast overrun % (selected method) | > 0% | > 10% |
| TCPI to BAC − CPI | > 0.10 → "completing within BAC considered unlikely" | — |

Overall label: Critical if any indicator is critical; otherwise **Insufficient data** if any indicator is unavailable; otherwise the worst of Warning/Favourable.
