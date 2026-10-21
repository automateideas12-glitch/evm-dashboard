---
title: "Viva Question Bank with Model Answers"
subtitle: "CE 725 · Topic 7: EVM Dashboard"
---

Worked numbers use the benchmark case (BAC ₹400 lakh). Period 1: PV 146, EV 128, AC 137. Period 2: PV 208, EV 176, AC 192 (₹ lakh). Practise answering without the tool.

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
27. **How did you validate the tool?** Benchmark solved on paper, with exact fractions and in a plain spreadsheet; compared with the dashboard through the upload pipeline in three input modes: 162/162 within one paisa. 79 automated tests; 7 injected errors all detected; browser tests of upload and manual entry.
28. **Why mutation testing?** Passing tests prove nothing if the tests cannot fail. Injecting known errors shows the tests detect them.

# G. AI and accountability

29. **Give one error AI made.** E.g. the AI's own test failed on a docstring; a UI bug reused a project name across uploads; it miscounted its own tests in the log. Each was found by running or re-checking, not by trusting the output.
30. **Who is accountable for a wrong EAC used in a claim?** The professional who used it. The tool states assumptions and limitations; it supports judgement.
31. **Confidentiality?** App runs locally; no upload leaves the machine; real cost data should not be pasted into public AI tools; synthetic data was used.
32. **Biggest practical limitation?** Honest measurement of physical progress — the tool checks consistency, not truth.

*[Team: add questions your own role is likely to face, and rehearse each member answering a random question from every section.]*
