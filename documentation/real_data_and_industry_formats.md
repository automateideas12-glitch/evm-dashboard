# Real project data and industry formats

## 1. Where the real data comes from

**DSLIB — empirical project database**, Operations Research & Scheduling group, Ghent University (Prof. Mario Vanhoucke). Release v3.4: 231 real projects, mostly construction (residential, commercial, institutional, civil). 117 of them include real progress-tracking periods. Each project was recorded in ProTrack, a project-scheduling and EVM tool, and exported to Excel.

- Download: <https://github.com/mariovanhoucke/DSLIB-Dynamic-Scheduling-Empirical-Project-Library/releases/latest> (file `DSLIB3.4.zip`, 131 MB; SHA-256 `19f87632…dc277` verified on 23-Oct-2026)
- Description: <https://www.projectmanagement.ugent.be/research/data/realdata>
- **Citation required when used:** Batselier, J. & Vanhoucke, M. (2015). Construction and evaluation framework for a real-life project database. *International Journal of Project Management*, 33(3), 697–710. <https://doi.org/10.1016/j.ijproman.2014.09.004>

Each project workbook contains a **Baseline Schedule** sheet with activities, WBS, dates, durations and fixed and variable costs. It has **one sheet per tracking period** (TP1, TP2, …), each listing every activity's actual start, actual duration, cumulative actual cost, % completed, EV and PV. A **Tracking Overview** sheet gives project-level PV, EV, AC, SPI and CPI per status date, together with Earned Schedule (ES/SPI(t)) metrics.

## 2. Projects converted for the dashboard (`data/real/`)

| Code | Project | Activities | Tracking periods | BAC (EUR) | Outcome |
|---|---|---:|---:|---:|---|
| C2014-05 | Apartment Building (1) | 25 | 13 | 532,410 | final AC €591,411: 11.1% over budget (CPI 0.900); finished 18-Oct-2012 vs baseline 15-Aug-2012 |
| C2013-06 | Government Office Building | 276 | 18 | 19,429,811 | final AC €21,546,846: 10.9% over budget |
| C2013-07 | Family Residence | 46 | 11 | 180,476 | final AC €175,031: 3.0% under budget |

For each project there are three files:
- `*_work_packages.csv` is loaded in **Work-Package-Level Data** mode.
- `*_evm.csv` holds the project totals, loaded in **Pre-calculated EVM Data** mode.
- `*_protrack_reference.csv` holds ProTrack's own PV/EV/AC/SPI/CPI, used for cross-checking.

To convert any other DSLIB project:

```bash
python tools/convert_dslib.py "DSLIB 3.4/Excel/<project>.xlsx" --out data/real/<name>
```

C2014-05 is available in the app under **Data → Load a built-in example → Real project**.

## 3. Validation against independent software

Our dashboard was run on the converted files and compared with ProTrack's recorded values for every tracking period (`tests/test_real_data.py`):

| Project | Mode | Max PV/EV/AC difference | Max CPI/SPI difference |
|---|---|---|---|
| C2014-05 | work package / pre-calculated | ≤ €0.005 | < 1×10⁻⁷ |
| C2013-06 | work package / pre-calculated | ≤ €0.04 | < 1×10⁻⁸ |
| C2013-07 | work package / pre-calculated | ≤ €0.001 | < 1×10⁻⁸ |

The cent-level differences come from rounding to 2 decimals in the CSV. This complements the synthetic hand-calculated benchmark: the benchmark checks the formulas, and this test shows the dashboard reproduces professional EVM software on real data.

### Discovery during conversion: "% complete" is not always physical progress

The first conversion used ProTrack's *Percentage Completed* column as actual progress. Work-package EV then came out up to **€32,405 lower** than ProTrack's EV, for example at TP3 of C2014-05. The cause:

- *Percentage Completed* is **duration-based**: elapsed days ÷ total days. For the excavation activity (*Bouwput + Kelders*) at TP1, 10 of 25 days had elapsed, giving 40%.
- ProTrack earns an activity's **fixed cost at its start** and its variable cost in proportion to progress. EV = €7,924.96 + 40% × €18,492 = €15,321.76, which is **58%** of the €26,416.96 budget.

The converter therefore uses **actual % = activity EV ÷ activity budget**. In industry, how EV is "earned" is an explicit choice: physical % complete, duration %, 0/100, 50/50, weighted milestones, or fixed costs earned at start. Using the wrong % column is a common real-world error. MS Project likewise distinguishes *% Complete*, which is duration-based, from *Physical % Complete* (see §4).

## 4. How industry tools hold the same data

| Concept | Our CSV column | Microsoft Project | Primavera P6 | ProTrack / DSLIB |
|---|---|---|---|---|
| Status date | `reporting_date` | Status Date | Data Date | Status date (per TP) |
| Activity / WBS element | `activity_id`, `activity_name` | ID, Name, WBS | Activity ID, Activity Name, WBS | ID, Name, WBS |
| Budget | `activity_budget` | Baseline Cost | Budget at Completion | Total Cost (baseline) |
| Planned value | derived, or `pv_cumulative` | BCWS | Planned Value Cost | Planned Value (PV) |
| Earned value | derived, or `ev_cumulative` | BCWP | Earned Value Cost | Earned Value (EV) |
| Actual cost | `ac_cumulative` | ACWP | Actual Total Cost | Actual Cost |
| Progress | `actual_progress_pct` (physical) | % Complete (duration) or Physical % Complete, chosen by *Earned Value Method* | Performance % Complete | Percentage Completed (duration) |

Sources: Microsoft, *Available fields reference* (<https://support.microsoft.com/office/available-fields-reference-615a4563-1cc3-40f4-b66f-1b17e793a460>); Oracle, *Primavera Analytics — Project Earned Value Breakdown* (<https://docs.oracle.com/cd/G19667_01/English/user/analytics_ref/81953.htm>); Planning Planet, *How to use Earned Value Management in Primavera P6* (<https://planningplanet.com/blog/how-use-earned-value-management-primavera-p6>).

**Is our format right for industry use?** Yes. The two practical routes are:
1. **Export BCWS/BCWP/ACWP**, or P6's Planned/Earned Value Cost and Actual Total Cost, per status date. Load them in **Pre-calculated EVM Data** mode; the column mapping recognises the names BCWS, BCWP and ACWP automatically.
2. **Export activity-level budget, progress and cost** per status date. Load them in **Work-Package-Level Data** mode, making sure the progress column is physical or earned %, not duration %.

In practice, companies keep the baseline and progress in the scheduling tool (P6 or MS Project) and actual cost in the accounting or ERP system. They export to Excel each reporting period, which is the same snapshot-per-status-date structure our CSV uses.

## 5. Forecast accuracy on a completed real project (C2014-05)

Actual final cost: €591,411 (BAC €532,410).

| Status date | % earned | CPI | SPI | EAC A (BAC/CPI) | error | EAC B (CPI×SPI) | error | EAC C (budget rate) | error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 08-Nov-2011 | 5 | 0.772 | 0.703 | 689,586 | +16.6% | 966,046 | +63.3% | 540,177 | −8.7% |
| 10-Jan-2012 | 23 | 0.802 | 0.819 | 663,492 | +12.2% | 776,828 | +31.4% | 562,421 | −4.9% |
| 10-Apr-2012 | 34 | 0.794 | 0.562 | 670,541 | +13.4% | 1,013,695 | +71.4% | 579,974 | −1.9% |
| 12-Jun-2012 | 64 | 0.876 | 0.793 | 607,785 | +2.8% | 664,211 | +12.3% | 580,934 | −1.8% |
| 07-Aug-2012 | 81 | 0.898 | 0.826 | 593,166 | +0.3% | 616,700 | +4.3% | 581,716 | −1.6% |
| 02-Oct-2012 | 98 | 0.901 | 0.978 | 591,138 | −0.0% | 591,443 | +0.0% | 589,818 | −0.3% |

Mean absolute error over the 12 interim periods: **A 8.7%, B 39.8%, C 3.2%**.

On this project most of the overspend occurred early (the excavation cost 47% more than budgeted) and later work ran closer to budget, so the budget-rate method was most accurate. Method B was distorted by very low SPI values. These conclusions apply to **one** project and should not be generalised. They show why the dashboard presents all methods with their assumptions rather than a single "correct" forecast.
