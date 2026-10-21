---
title: "Final Presentation Outline — 15 min + 5 min questions"
subtitle: "CE 725 · Topic 7: EVM Dashboard"
---

Timing assumes 10 slides plus a 5-minute live demo. Speaker allocation is a suggestion; every member must be able to answer questions on any slide.

| # | Slide | Content (keep slides light; detail is in speaker notes) | Time | Suggested speaker |
|---|---|---|---|---|
| 1 | Title and team | Project, topic, five names and roles | 0:20 | Prashant |
| 2 | The problem | Overruns found too late. A budget-vs-actual report says "₹137 lakh spent vs ₹146 lakh planned — under budget"; EVM says the same project is behind *and* over cost (benchmark P1). | 1:00 | Prashant |
| 3 | EVM in one picture | PV/EV/AC S-curve with CV and SV marked; CPI, SPI in one line each; "SV is money, not days" | 1:30 | Prashant |
| 4 | What the tool does | Three input modes; validation; 5 tabs; offline; architecture (engine separate from UI) | 1:00 | Sobhith |
| 5 | **Live demo** | Overview signboard → Trends → switch forecast method A/B/C → Commentary → Data: upload the faulty file (errors, no load) → load the benchmark example | 5:00 | Sobhith (driving), Varun (narrating data) |
| 6 | Forecasting | Four EAC methods and their assumptions; demo project EAC range ₹1,245.5–1,312.7 lakh; TCPI 1.136 vs CPI 0.947 → BAC unlikely | 1:30 | Prashant |
| 7 | Validation | Benchmark P1/P2 by hand; three independent routes; 162/162 comparisons pass at ≤1 paisa; 7/7 injected formula errors caught; edge cases | 1:45 | Arjun |
| 8 | What AI got wrong | Defects D1–D6 and the log miscount; why browser and mutation testing were needed | 1:15 | Shreyansh |
| 9 | Practical relevance and limits | Who would use it; progress measurement is the hard part; SPI caveat; synthetic data; what real use needs | 1:00 | Varun |
| 10 | Conclusions | What we learned; next steps (Earned Schedule, re-baselining, scheduler integration) | 0:40 | Shreyansh |

**Demo safety:** rehearse with the built-in examples; keep `data/` files on the laptop; have screenshots (`reports/screenshots/`) as a fallback if the laptop fails; run offline once beforehand.

**Backup slides (for questions):** benchmark P2 working; formula reference table; health-threshold rules; data dictionary; TCPI identities.
