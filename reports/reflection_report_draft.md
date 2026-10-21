---
title: "Learnings and Reflection Report — DRAFT"
subtitle: "CE 725 · Topic 7: EVM Dashboard"
---

> **How to use this draft.** Structure follows Section 7 of the course guidelines (target 10–15 pages). Sections 1–4 and 6 are drafted from what actually happened in the build, with evidence references; rewrite them in the team's own words and add your own examples. Section 5 (individual reflections) contains only prompts — each member must write their own half page. Text in *[square brackets]* must be replaced. Do not submit unedited AI-drafted reflection as the team's own: the guidelines treat undisclosed or unverified AI output as misconduct.

# 1. Subject learnings

**EVM separates three questions that ordinary cost tracking blurs.** A budget-vs-actual report compares AC with the budget to date and cannot tell whether an under-spend means efficiency or simply less work done. Introducing EV — the budgeted value of work actually performed — splits the question: CV = EV − AC isolates cost efficiency and SV = EV − PV isolates progress against plan. In the benchmark, Period 1 shows AC (₹137 lakh) *below* PV (₹146 lakh), which a naive reading calls "under budget"; EV (₹128 lakh) shows the project is both behind (SV −₹18 lakh) and over cost for the work done (CV −₹9 lakh).

**Cumulative vs period data is the most practical trap.** EVM status values are cumulative to the status date. Adding cumulative values double-counts; treating period costs as cumulative understates AC. The tool therefore makes the distinction explicit in the data model and never sums cumulative columns. *[Add the team's own example of where this confused you.]*

**Weighting matters.** Project progress is not the average of activity percentages. In Period 2 the unweighted mean (41.25%) understates the budget-weighted progress (44%) by ₹11 lakh of EV because the large RCC package is further along than the small ones.

**SPI is a value measure, not a time measure.** SV is in rupees; SPI tends to 1.00 at completion even for a late project because PV and EV both reach BAC. Schedule delay must be judged from the programme (critical path); Earned Schedule is the usual extension. *[Did the team know this before the project?]*

**Forecasts are assumptions made explicit.** BAC/CPI, AC + (BAC−EV)/(CPI×SPI) and AC + (BAC−EV) are not competing "right answers" but statements about the future. For the demo project at Sep-2026 they range from ₹1,245.5 lakh to ₹1,312.7 lakh. The spread is decision information in itself.

**TCPI turns a forecast into a feasibility test.** To finish the demo project within BAC, remaining work would need TCPI 1.136 against a CPI achieved so far of 0.947 — an improvement rarely achieved without changing scope, method or budget. Once AC ≥ BAC with work left, TCPI to BAC is undefined: the original budget is no longer achievable.

**Undefined is not zero.** CPI with AC = 0 is undefined, not 0 and not infinity. Treating undefined as zero would make a new project look catastrophically inefficient, or a missing index look healthy.

# 2. AI capability assessment

**Where AI accelerated the work.** *[Team: confirm and expand from your own experience.]* Structuring the application into separate calculation, validation and interface layers; producing the first version of all formulas and their guard conditions; generating a large test suite quickly; writing data-validation rules for many edge cases; drafting documentation from the actual test outputs.

**Where AI was wrong or needed correction — documented examples** (AI usage log entries 10, 13–15, 17; validation report §7):

1. *Faulty test.* The AI's own test for benchmark independence searched for the text "from src" and failed on a docstring — a false alarm that would have been "fixed" wrongly by someone who did not read the failure.
2. *Interface state bug.* A project name typed for a rejected file was silently reused for the next valid file. Unit tests could not catch this; only end-to-end testing in a browser did.
3. *Duplicate and inconsistent error messages* in validation output.
4. *Layout defects* (clipped headings, truncated labels, overlapping chart annotations) that the code did not report as errors but a human reviewer would.
5. *Automation limit.* The AI could not make a scripted browser edit register in the data-entry grid; this remains a manual check rather than being claimed as tested.
6. *Self-reporting error.* While drafting the AI usage log, the AI stated "28 validation tests"; the actual count was 36. It was corrected only because the figure was re-checked by running the tests.

*[Add any errors the team found itself — e.g. formulas you questioned, explanations you found unclear, places where the AI's EVM interpretation differed from your textbook. These carry the most weight for marks.]*

**Pattern observed.** A first-run pass of every benchmark value is not proof of correctness; mutation testing (deliberately inserting seven common formula errors, all caught) was needed to show the tests could fail. AI output was most reliable where it could be checked mechanically against an independent calculation, and least reliable where correctness depended on behaviour across a user session.

# 3. Validation insights

- Three independent routes (paper, exact fractions, plain spreadsheet) agreed before any comparison with the dashboard; disagreement among them would have pointed to an error in the benchmark itself.
- Tolerances were set at one paisa and 10⁻⁹ and values compared at full precision; rounding both sides first can hide real discrepancies.
- The benchmark deliberately included cost without progress and a budget-weighting trap, because a benchmark that avoids hard cases validates little.
- The precision finding (₹0.40 from percentages rounded to 6 decimals) showed that input format, not only formulas, affects results.
- *[Team: what did doing the paper calculation yourselves reveal? Record the time it took and any slip you made — it shows why tools help.]*

# 4. Practical relevance

*[Ideally replace with feedback from a practising engineer, contractor or lender — bonus credit; record name/role only with permission.]*

**Who would use it.** A contractor's project-controls engineer for monthly reporting; a client's project-management consultant reviewing contractor claims of progress; a lender's engineer monitoring drawdowns against progress.

**What would need to change for real use.** Integration with the scheduling tool (Primavera/MS Project) and the cost ledger; re-baselining and change-order handling; contingency and management reserve; Earned Schedule for time-based forecasts; multi-user access with audit trail; agreed progress-measurement rules per work type (e.g. steps for RCC: shuttering, reinforcement, concreting); approval workflow for forecasts.

**The hardest real-world input is physical progress.** The arithmetic is simple; measuring EV honestly is not. The tool can enforce consistency but cannot verify that "55% complete" is true.

# 5. Individual reflections (half a page each — written by each member)

Prompts: What did your role require in practice? What did you personally learn about EVM or construction finance? One moment AI helped you, and one where it misled you or you had to correct it. What would you do differently?

**Prashant Kumar — Project Lead and Finance Modeller.** *[To be written by Prashant.]*

**Varun Chandak — Data Lead.** *[To be written by Varun.]*

**Sobhith R — AI and Tool Developer.** *[To be written by Sobhith.]*

**Arjun Andhare — Validation Engineer.** *[To be written by Arjun; include your own paper re-calculation of the benchmark.]*

**Shreyansh Singh — Documentation and Reflection Lead.** *[To be written by Shreyansh.]*

# 6. Ethics and limitations

**Data reliability.** EVM outputs inherit every weakness of the progress and cost data. A tool that presents ₹-precise EAC values can create false confidence; the dashboard therefore labels forecasts as assumption-based and shows the spread between methods.

**Over-reliance on AI.** Every AI-generated formula was tested against an independent calculation, and the defects above show why. The team must be able to explain each formula without the tool (individual viva).

**Accountability.** Decisions based on these numbers — claims, payments, corrective action — remain the responsibility of the professionals who make them. Health labels are screening rules, not judgements.

**Confidentiality and privacy.** The app runs locally and does not transmit uploaded data. Real project cost data is commercially sensitive; it should not be pasted into public AI tools, and synthetic data was used throughout development. *[Team: state your own policy and whether any real data was used.]*

**Limitations of simplified progress measurement and forecasts.** Project-level percentages hide which work is late; SPI does not measure critical-path delay; forecasts must never be presented as guarantees (see `documentation/assumptions_and_limitations.md`).

**Disclosure.** This report and the tool were developed with substantial AI assistance, disclosed in the AI usage log.
