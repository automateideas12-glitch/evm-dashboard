---
title: "Viva Question Bank with Model Answers"
subtitle: "CE 725 · Topic 7: EVM Dashboard"
---

Sections A–G use the synthetic benchmark case (BAC ₹400 lakh); section H uses the real manual check case. Period 1: PV 146, EV 128, AC 137. Period 2: PV 208, EV 176, AC 192 (₹ lakh). Practise answering without the tool.

# A. PV, EV, AC

1. **Define PV, EV and AC.** PV: budgeted value of work *scheduled* by the status date. EV: budgeted value of work *actually done*. AC: cost actually incurred for that work. All cumulative.
2. **How is EV measured in a building project?** Physical progress of each work package (quantities installed, milestones) × its budget, summed. Not time elapsed, not money spent.
3. **Why not average the work-package percentages?** Packages differ in budget. P2: simple average 41.25% → EV 165; weighted 44% → EV 176.
4. **Can AC rise while EV stays the same?** Yes — advances, rework, idle time. The tool does not flag it as an error; commentary suggests checking it.

# B. CV and SV

5. **Compute CV and SV for Period 1.** CV = 128 − 137 = −9; SV = 128 − 146 = −18 (₹ lakh). Both unfavourable.
6. **Is SV = −18 lakh "18 days late"?** No. SV is budget value. Delay in time needs the programme or Earned Schedule.
7. **AC < PV in Period 1 — under budget?** No. Comparing AC with PV mixes cost and progress. EV shows less work was done than planned and it cost more than its budget.

# C. CPI and SPI

8. **CPI and SPI for Period 2?** CPI = 176/192 = 0.917; SPI = 176/208 = 0.846.
9. **Interpret CPI 0.917.** ₹0.92 of budgeted work earned per ₹1 spent.
10. **What happens to SPI at completion?** EV = PV = BAC so SPI = 1.00, even if the project finished late.
11. **CPI when AC = 0?** Undefined (division by zero). The tool shows "Undefined" with the reason, never 0.

# D. EAC and ETC

12. **EAC by BAC/CPI for P2.** 400/0.9167 = 400 × 192/176 = 436.36; ETC = 244.36; VAC = −36.36.
13. **EAC by AC + (BAC−EV)/(CPI×SPI) for P2.** CPI×SPI = 0.7756; 224/0.7756 = 288.79; EAC = 480.79.
14. **EAC by AC + (BAC−EV) for P2.** 192 + 224 = 416.
15. **Which method is correct?** None is "correct": each states an assumption (efficiency continues; schedule pressure adds cost; past variance was one-off). Choose by judgement about the cause of the variance; show the range.
16. **Why is method B usually highest here?** Both indices < 1, so their product is smaller and the remaining work is divided by a smaller number.
17. **When is method C justified?** When the cause of past overspend has been removed and future work is expected at budget rate.
18. **What is method D?** A bottom-up re-estimate of remaining work: EAC = AC + ETC(user).
19. **Can ETC be negative?** Only from bad inputs or a misapplied method; the tool flags it for review rather than setting it to zero.

# E. TCPI

20. **TCPI to BAC for P2.** (400−176)/(400−192) = 224/208 = 1.077.
21. **Interpret.** Remaining work must earn ₹1.077 per ₹1 spent to finish within BAC — versus 0.917 achieved. Gap 0.16 > 0.10 screening rule → unlikely.
22. **TCPI to BAC when AC > BAC?** Undefined: the original budget is already exceeded with work remaining.
23. **TCPI to the BAC/CPI forecast always equals?** CPI. (To method C's EAC it is 1; to method B's it is CPI×SPI.)

# F. Data and validation

24. **Cumulative vs period values?** Cumulative = total to date; period = this month only. Never add cumulatives; period AC is summed only if no cumulative AC exists.
25. **What does the tool do with a missing value?** Blocks loading with the row and field; never treats it as zero.
26. **A cumulative value decreases — error?** Warning: may be a re-measurement or credit; the value is not changed; the user must explain or correct.
27. **How did you validate the tool?** Twice. Part A: synthetic benchmark solved on paper, with exact fractions and in a plain spreadsheet, compared with the dashboard through the upload pipeline in three input modes: 162/162 values within one paisa. Part B: a real project (manual check case) with a 502-formula hand-calculation workbook: 90/90 values within one cent for all five reports, plus every work package. 164 automated tests; 33 deliberately injected errors all detected; real-browser tests of upload, smart reader and manual entry.
28. **Why mutation testing?** Passing tests prove nothing if the tests cannot fail. Injecting known errors shows the tests detect them.

# G. AI and accountability

29. **Give one error AI made.** It built a separate app instead of changing ours (caught by the team); it labelled CPI 0.86 "Amber" when our rule makes it Critical (caught by hand-calculated tests); it wrote CPI 0.714 instead of 0.713 (caught by an interface test); it guessed a €3 tolerance when the real gap was €3.79. Each was found by running or re-checking, not by trusting the output (AI log 26, 27, 34, 35).
30. **Who is accountable for a wrong EAC used in a claim?** The professional who used it. The tool states assumptions and limitations; it supports judgement.
31. **Confidentiality?** The app runs locally and no upload leaves the machine; the file reader is rule-based, not an online AI service, by team decision. Real data used comes from the public DSLIB research database (cited); synthetic and interpolated data are labelled. Commercial cost data should not be pasted into public AI tools.
32. **Biggest practical limitation?** Honest measurement of physical progress — the tool checks consistency, not truth.

# H. The manual check case (real data) — amounts in €

Inputs at 31-Dec-2013: budgets WP1 49,231.67, WP2 58,025.66, WP3 78,356.70, WP4 28,803.68 (BAC 214,417.71); actual % 100, 58.03, 22.27, 39.49; AC 39,821.67, 69,412.98, 40,197.69, 7,162.11. Final cost 224,789.67 on 28-Feb-2014 (baseline finish 20-Dec-2013).

33. **Where does the data come from, and why group it?** DSLIB C2015-33 (Batselier & Vanhoucke, 2015), a real Belgian civil-works project recorded in ProTrack. 12 activities were grouped into 4 work packages and percentages rounded to 2 decimals so it can be checked with a calculator; the file still matches ProTrack's own PV/EV/AC within €3.79 (bound €10.72).
34. **Compute EV and CPI at 31-Dec-2013.** EV = 49,231.67 + 58,025.66×0.5803 + 78,356.70×0.2227 + 28,803.68×0.3949 = 111,728.57; CPI = 111,728.57 / 156,594.45 = 0.713.
35. **Why is PV equal to BAC on 31-Dec-2013?** The baseline finish (20-Dec-2013) has passed, so all work was scheduled to be done.
36. **TCPI at 31-Dec-2013 is 1.776. Meaning?** Every remaining euro would have to earn €1.78 of value, against 0.71 achieved — not credible; the budget was already lost. The project finished at €224,790, over BAC.
37. **On 30-Nov-2013 WP4 shows "Insufficient data". Why?** It earned €5,686 of value although none was planned yet (PV = 0, early start), so SPI = EV/PV is undefined.
38. **The project finished two months late. Why is the final SPI 1.00?** At completion EV = PV = BAC. SPI measures the rate of earning value, not time; delay needs the programme or Earned Schedule.
39. **How good were the forecasts at about 50 % complete?** Against the real final cost: A +33.7 %, B +92.5 %, C +15.3 %. A second project (C2014-05, 50 % point interpolated) gave A +7.0 %, B +32.5 %, C −1.5 %. The formulas were right; the assumptions behind them did not hold, because the early overspend was not repeated.
40. **Where was the problem on 30-Nov-2013?** Project CV −€25,905, but earthworks alone −€31,820 (CPI 0.373), partly offset by demolition +€6,986. The project total hides it; the work-package table shows it.

# I. The tool

41. **What does the smart reader do, and is it AI?** It is rule-based and offline: it finds the header row, a status date above the table, fractions and lakh/crore amounts, totals rows, and matches columns only when header and values both fit. No machine learning or online service, so its behaviour is testable and no data leaves the computer.
42. **Why is MS Project's "% Complete" not used as progress?** It is duration progress (time elapsed on the task), not physical work done; using it would make EV follow the calendar.
43. **What happens if a file carries its own PV and EV columns?** They are cross-checked row by row against budget × progress %; any mismatch is named with both values.
44. **Why are health thresholds adjustable?** They are screening rules chosen by the team (Warning < 1.00, Critical < 0.90; overrun > 0 % and > 10 %), not industry standards.

*[Team: add questions your own role is likely to face, and rehearse each member answering a random question from every section.]*
