# Project Charter — CE 725 Construction Economics and Finance

Format follows Annexure B of the course project guidelines. Items carried over unchanged from the team's submitted charter are marked **[original]**; items added or completed during development are marked **[added]**.

| Item | Details |
|---|---|
| **Team number** | _To be filled by the team (not stated in the materials provided)._ |
| **Team members and roles** [original] | 24B0611 – Prashant Kumar — Role 1: Project Lead & Finance Modeller<br>23B2466 – Varun Chandak — Role 2: Data Lead<br>26M0617 – Sobhith R — Role 3: AI & Tool Developer<br>23B2419 – Arjun Andhare — Role 4: Validation Engineer<br>26M0609 – Shreyansh Singh — Role 5: Documentation & Reflection Lead |
| **Topic selected** [original] | Topic 7 — Earned Value Management (EVM) Dashboard |
| **Problem statement** [original, unchanged] | Construction projects can face cost overruns and schedule delays that are identified too late for corrective action. Project managers need a simple way to compare planned progress, earned value and actual expenditure. The proposed EVM Dashboard will monitor project performance using key Earned Value Management indicators such as PV, EV, AC, CPI, SPI, EAC, ETC and TCPI. It will present these metrics through clear dashboards and trend charts, helping users identify deviations from the planned project performance and take timely corrective action. |
| **Intended users of the tool** [original] | Project managers, construction managers, project control engineers, contractors, clients/owners and quantity surveyors. |
| **Method(s) to be applied** [added] | Earned Value Management (cumulative, multi-period): PV, EV, AC, CV, SV, CPI, SPI; EAC by three formula methods (BAC/CPI; AC + (BAC−EV)/(CPI×SPI); AC + (BAC−EV)) plus a user-entered independent ETC; ETC, VAC, forecast overrun; TCPI against BAC and against EAC. Work-package-weighted EV (budget-weighted, never an unweighted average). Transparent, configurable screening thresholds for project health. |
| **Data sources** [added] | Synthetic, clearly labelled illustrative datasets created for this project (a 4-work-package G+4 residential block benchmark and a 12-month demonstration project). No confidential or real client data is used. Real project data may be uploaded by users at run time; it stays on the machine running the app. |
| **Build platform** [added] | Python 3, Streamlit (interface), Pandas (data handling), Plotly (charts), pytest (automated tests). Runs locally; core calculations need no internet connection or LLM. |
| **Benchmark case for validation** [added] | Illustrative G+4 RCC residential block, BAC ₹4.00 crore, 4 work packages, two monthly reporting periods (31-Jan-2026 and 28-Feb-2026). All indices solved by hand with intermediate values, and in a plain-formula spreadsheet, then compared with the dashboard. See `reports/validation_report.md`. |
| **Key risks to completion** [added] | (1) Formula or sign-convention errors in AI-generated code — mitigated by independent benchmark and unit tests. (2) Confusing cumulative and period values — mitigated by explicit data model and validation. (3) Undefined indices (division by zero) shown as misleading numbers — mitigated by explicit "undefined" handling. (4) Schedule: ~4-week window to 1 Nov — mitigated by building the validated core before optional features. (5) AI usage log not maintained contemporaneously — the team must log genuine entries as work proceeds. |

## Points needing team confirmation

1. **Spelling of the Validation Engineer's surname.** The submitted charter image reads "Arjun **Andhare**"; the development brief reads "Arjun **Bhadare**". This charter uses the charter-image spelling. Please confirm and correct across all documents (a single find-and-replace).
2. **Team number** — not present in the materials provided.
