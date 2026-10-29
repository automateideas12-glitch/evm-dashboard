---
title: "Final Presentation Outline — 15 min + 5 min questions"
subtitle: "CE 725 · Topic 7: EVM Dashboard · matches the slide deck of 29-Oct-2026"
---

The slide deck (16 slides, speaker notes on every slide) is published as a Slides artifact and can be downloaded as PowerPoint or PDF. Timing: slides 2–7 about 5 minutes, live demonstration 5 minutes, slides 9–15 about 5 minutes. Speakers are a suggestion; **every member must be able to explain any formula or number** (course guidelines, Section 6).

| # | Slide | Key content | Time | Speaker |
|---|---|---|---|---|
| 1 | Earned Value Management Dashboard | Team and roles; the question the tool answers | 0:20 | Prashant |
| 2 | A cost report can call a losing project "under budget" | Benchmark 31-Jan-2026: AC ₹137 lakh < PV ₹146 lakh, yet EV ₹128 lakh → CV −9, SV −18 | 1:00 | Prashant |
| 3 | Earned value in one table | PV, EV, AC, CV, SV, CPI, SPI, EAC, TCPI: formula, meaning, good sign | 1:15 | Prashant |
| 4 | From a site sheet to a decision in five steps | Read → Check → Calculate → Explain → Export; three input types; offline | 0:45 | Sobhith |
| 5 | It starts from your file, as it is | Home screen; smart reader on the team's site sheet | 0:30 | Sobhith |
| 6 | One screen: how bad, where, and what next | Top bar, health banner, explained figures (manual check case, 31-Dec-2013) | 0:30 | Sobhith |
| 7 | Where the problem is, on the main screen | S-curve, combined CPI/SPI chart, work-package status, top problem activities | 0:40 | Sobhith |
| 8 | **Live demonstration** | Script below | 5:00 | Sobhith (driving), Varun and Arjun (narrating) |
| 9 | A real project you can check by hand | IJzertoren (DSLIB C2015-33), 4 WPs, 5 reports; hand vs dashboard at 31-Dec-2013; 90/90 | 0:50 | Arjun |
| 10 | Validated against independent hand calculations | 162/162 synthetic, 90/90 real, 164 tests, 33/33 injected errors caught, D1–D16 | 0:50 | Arjun |
| 11 | Correct formulas, poor forecasts at mid-project | Forecast chart; errors at ~50 %: A +33.7 %, B +92.5 %, C +15.3 % (C2015-33); +7.0 %, +32.5 %, −1.5 % (C2014-05) | 1:00 | Prashant |
| 12 | The total hides where the problem is | 30-Nov-2013: project CV −€25,905; earthworks −€31,820 | 0:30 | Varun |
| 13 | What AI got wrong, and how we caught it | 37 log entries (24/11/2); six specific errors and the check that caught each | 1:00 | Shreyansh |
| 14 | Who would use it, and what real use needs | Contractor, consultant, lender; integration, change control, Earned Schedule, progress rules, audit trail | 0:30 | Varun |
| 15 | What we learned | Three learnings; next steps; questions | 0:20 | Shreyansh |
| 16 | Backup: benchmark period 2 by hand | For questions only | — | Arjun |

# Live demonstration script (5 minutes)

| Time | Step | What to say or point out |
|---|---|---|
| 0:00 | Home → **Manual check case (real)** | Real Belgian project; the hand-calculation workbook downloads from the home screen |
| 0:30 | Banner at 31 Dec 2013 | Critical; CPI 0.713, SPI 0.521, EAC (A) €300,520 — read the same row in the workbook's *Project calculation* sheet |
| 1:30 | Top bar → reporting date **30 Nov 2013** | WP4 shows *Insufficient data*: value earned before any was planned (PV = 0, SPI undefined) |
| 2:15 | Method **A → B → C**, then *Forecasts* tab | B is the most pessimistic; compare each EAC with the real final cost €224,790 (workbook *Forecast check* sheet) |
| 3:15 | *Commentary* tab | Rule-based text: facts, change since last report, forecast, what to investigate; never claims a cause |
| 3:45 | **← Home** → upload `data/demo_files/site_status_sheet.xlsx` (Work-Package-Level) | Smart reader: header on row 4, status date above the table, fractions → %, totals row removed, missing actual cost asked for. Optional: `site_sheet_with_pv_ev_ac.xlsx` shows the row-by-row PV/EV cross-check |
| 4:30 | Upload `data/demo_files/faulty_upload_progress.csv` (Progress-Based) | Errors name the spreadsheet row and the fix; there is no *Open dashboard* button |

**Demo safety.** Rehearse twice. Open the app once beforehand (Streamlit Cloud can take a minute to wake; run `streamlit run app.py` locally as a backup). Keep the two demo files and the workbook on the desktop. If anything fails, switch to `reports/screenshots/` and carry on; do not debug live.

**Likely questions** (see `viva_question_bank.md`): SPI = 1.00 at completion for a late project; why method B is highest; TCPI above CPI; weighted vs simple average; undefined vs zero; who is accountable for a decision based on the tool; why no online AI service in the app.
