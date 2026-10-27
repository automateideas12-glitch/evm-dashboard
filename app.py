"""
CE 725 — Earned Value Management (EVM) Dashboard
Streamlit interface. All calculations live in src/ and are shared by the
upload and manual-entry workflows.

Run:  streamlit run app.py
"""
from __future__ import annotations

import io
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from src import __version__
from src.analysis import NOT_STARTED, problem_activities, work_package_status
from src.charts import (budget_vs_forecast_chart, combined_index_chart, cumulative_chart, eac_trend_chart,
                        progress_chart, wp_variance_chart)
from src.commentary import (CRITICAL, FAVOURABLE, INSUFFICIENT, WARNING, HealthThresholds, classify,
                            generate_commentary)
from src.data_processing import (FIELDS, MODE_FIELDS, MODES, ProcessedData, ProjectSettings, excel_sheet_names,
                                 mode_fields, prepare, read_table, suggest_mapping, template)
from src.evm_calculations import compute_results, metric_from_row
from src.forecasting import METHODS
from src.formatting import format_index, format_metric, format_money
from src.smart_reader import (entry_label, understand, values_entry_table, with_entered_values,
                              workbook_with_missing_columns)
from src.validation import is_missing

ROOT = Path(__file__).parent
DATA = ROOT / "data"

st.set_page_config(page_title="EVM Dashboard — CE 725", page_icon="📐", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stMetric, button, input, textarea, select {
  font-family: Barlow, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
h1, h2, h3 { letter-spacing: -0.01em; color: #1F2A33; }
.block-container { padding-top: 3.2rem; max-width: 1400px; }
.signboard { display:flex; align-items:stretch; border:2px solid #1F2A33; margin: 0 0 1.2rem 0;
  background:#fff; }
.signboard .sb-state { padding: .9rem 1.4rem; font-size: 1.9rem; font-weight: 700; color:#fff;
  min-width: 13rem; display:flex; align-items:center; }
.signboard .sb-body { padding: .7rem 1.2rem; display:flex; flex-direction:column; justify-content:center; }
.signboard .sb-title { font-size: 1.35rem; font-weight: 600; color:#1F2A33; line-height:1.2; }
.signboard .sb-meta { font-size: .98rem; color:#4A5560; margin-top:.15rem; }
.sb-Favourable .sb-state { background:#2E7D4F; }
.sb-Warning .sb-state { background:#E3A008; color:#1F2A33; }
.sb-Critical .sb-state { background:#B3261E; }
.sb-Insufficient .sb-state { background:#6B7280; }
.demo-note { border-left: 4px solid #E3A008; background:#FFF8E6; padding:.55rem .9rem; margin-bottom:1rem;
  color:#1F2A33; }
[data-testid="stMetricValue"] { font-size: 1.55rem; font-weight: 600; }
.section-intro { color:#4A5560; margin-top:-.4rem; margin-bottom:.6rem; max-width: 75ch; }
.hero { border:2px solid #1F2A33; background:#fff; padding:1.2rem 1.5rem; margin-bottom:1.2rem; }
.hero-title { font-size:2.2rem; font-weight:700; color:#1F2A33; line-height:1.1; }
.hero-sub { font-size:1.05rem; color:#4A5560; margin-top:.35rem; max-width:80ch; }
</style>
""", unsafe_allow_html=True)

KPI_HELP = {
    "bac": "Budget at Completion: the total approved budget for the scope being measured.",
    "pv": "Planned Value: budgeted value of the work SCHEDULED to be done by the reporting date (cumulative).",
    "ev": "Earned Value: budgeted value of the work ACTUALLY DONE by the reporting date (cumulative). "
          "EV = % of budgeted scope physically complete × budget.",
    "ac": "Actual Cost: cost actually incurred for the work performed up to the reporting date (cumulative).",
    "cv": "Cost Variance = EV − AC. Negative means the work done cost more than its budget.",
    "sv": "Schedule Variance = EV − PV, in money terms (not days). Negative means less work was earned than planned.",
    "cpi": "Cost Performance Index = EV / AC. Below 1.00 = budgeted value earned per unit of money spent is less "
           "than 1 (unfavourable).",
    "spi": "Schedule Performance Index = EV / PV. Below 1.00 = work is being earned slower than planned. Tends to "
           "1.00 at completion even for late projects.",
    "eac": "Estimate at Completion under the selected forecasting method (sidebar). A forecast, not a guarantee.",
    "etc": "Estimate to Complete = EAC − AC: forecast cost still to be spent.",
    "overrun": "Forecast overrun = EAC − BAC (= −VAC). Positive = forecast to finish over budget. This is a "
               "forecast, not an overrun already incurred.",
    "vac": "Variance at Completion = BAC − EAC. Negative = forecast to finish over budget.",
    "tcpi_bac": "To-Complete Performance Index to BAC = (BAC − EV) / (BAC − AC): the cost efficiency the "
                "remaining work must achieve to finish within the original budget.",
    "tcpi_eac": "TCPI to EAC = (BAC − EV) / (EAC − AC): efficiency needed to finish at the selected EAC.",
    "pct": "Percentages of BAC: planned (PV/BAC), earned (EV/BAC) and spent (AC/BAC).",
}
PROJECT_TYPES = ["Building — residential", "Building — commercial", "Building — institutional", "Infrastructure",
                 "Industrial", "Other"]


# ---------------------------------------------------------------- state helpers
def make_current(p: ProcessedData, label: str) -> dict:
    return {"processed": p, "label": label, "etc_overrides": {}, "loaded_at": datetime.now()}


def load_dataset(path: Path, mode: str, settings: ProjectSettings, label: str) -> ProcessedData:
    raw = read_table(path.read_bytes(), path.name)
    return prepare(raw, suggest_mapping(list(raw.columns), mode), settings, mode)


def demo_project() -> dict:
    s = ProjectSettings(project_type="Building — commercial", baseline_start=datetime(2026, 1, 1).date(),
                        baseline_finish=datetime(2026, 12, 31).date(), project_manager="(illustrative)")
    p = load_dataset(DATA / "sample_project_work_packages.csv", "work_package", s, "demo")
    return make_current(p, "Demo project — synthetic data")


def real_project() -> dict:
    s = ProjectSettings(project_type="Building — residential", currency="EUR",
                        baseline_start=datetime(2011, 10, 3).date(), baseline_finish=datetime(2012, 8, 15).date(),
                        reporting_frequency="Irregular")
    p = load_dataset(DATA / "real" / "C2014-05_apartment_building_work_packages.csv", "work_package", s, "real")
    return make_current(p, "REAL project data — DSLIB C2014-05 (Batselier & Vanhoucke, 2015)")


def benchmark_project() -> dict:
    s = ProjectSettings(project_type="Building — residential", baseline_start=datetime(2025, 10, 1).date(),
                        baseline_finish=datetime(2026, 9, 30).date())
    p = load_dataset(DATA / "benchmark_case_work_packages.csv", "work_package", s, "bench")
    return make_current(p, "Benchmark case — synthetic data")


def current_results(cur: dict) -> pd.DataFrame:
    p: ProcessedData = cur["processed"]
    periods = p.periods.copy()
    for d, v in cur["etc_overrides"].items():
        periods.loc[periods["reporting_date"] == d, "independent_etc"] = v
    return compute_results(periods, p.bac)


# ---------------------------------------------------------------- data entry (home + Data tab)
def settings_form(prefix: str, base: ProjectSettings, mode: str, bac_in_file=None) -> ProjectSettings:
    c = st.columns(3)
    name = c[0].text_input("Project name *", base.name, key=f"{prefix}_name")
    ptype = c[1].selectbox("Project type", PROJECT_TYPES,
                           index=PROJECT_TYPES.index(base.project_type) if base.project_type in PROJECT_TYPES else 5,
                           key=f"{prefix}_type")
    cur_opts = ["INR", "USD", "EUR", "GBP"]
    currency = c[2].selectbox("Currency", cur_opts, index=cur_opts.index(base.currency) if base.currency in cur_opts else 0,
                              key=f"{prefix}_cur")
    c = st.columns(3)
    if mode == "work_package":
        bac = c[0].number_input("Project BAC (optional — checked against WP budgets)", min_value=0.0, value=None,
                                step=100000.0, key=f"{prefix}_bac")
    elif bac_in_file is not None:
        c[0].text_input("BAC (from file)", f"{bac_in_file:,.2f}", disabled=True, key=f"{prefix}_bacf")
        bac = None
    else:
        bac = c[0].number_input("BAC * (full amount)", min_value=0.0,
                                value=float(base.bac) if base.bac else None, step=100000.0, key=f"{prefix}_bac")
    bs = c[1].date_input("Baseline start", value=base.baseline_start, key=f"{prefix}_bs")
    bf = c[2].date_input("Baseline completion", value=base.baseline_finish, key=f"{prefix}_bf")
    c = st.columns(3)
    freq = c[0].selectbox("Reporting frequency", ["Monthly", "Weekly", "Irregular"],
                          index=["Monthly", "Weekly", "Irregular"].index(base.reporting_frequency), key=f"{prefix}_fq",
                          help="Used to detect missing reporting periods.")
    pm = c[1].text_input("Project manager (optional)", base.project_manager, key=f"{prefix}_pm")
    dayfirst = c[2].radio("Non-ISO dates are written as", ["DD/MM/YYYY", "MM/DD/YYYY"],
                          index=0 if base.dayfirst else 1, horizontal=True, key=f"{prefix}_df",
                          help="YYYY-MM-DD dates are always read unambiguously.") == "DD/MM/YYYY"
    return ProjectSettings(name=name.strip(), project_type=ptype, currency=currency,
                           bac=float(bac) if bac else None, baseline_start=bs or None, baseline_finish=bf or None,
                           project_manager=pm, reporting_frequency=freq, dayfirst=dayfirst)


def show_validation(p: ProcessedData):
    rep = p.report
    bad_rows = len(rep.rows_with_errors())
    c = st.columns(4)
    c[0].metric("Records read", rep.records_read)
    c[1].metric("Records without errors", max(rep.records_read - bad_rows, 0))
    c[2].metric("Blocking errors", len(rep.errors))
    c[3].metric("Warnings", len(rep.warnings))
    if rep.issues:
        st.dataframe(rep.to_frame(), hide_index=True, width="stretch")
    if p.ok:
        st.success("Validation passed. Review any warnings, then load the data.")
        show = p.periods[["reporting_date", "planned_pct", "actual_pct", "pv", "ev", "ac"]].copy()
        show["reporting_date"] = show["reporting_date"].dt.strftime("%Y-%m-%d")
        show.columns = ["Reporting date", "Planned %", "Actual %", "PV", "EV", "AC"]
        st.caption("Processed reporting periods (sources: " +
                   "; ".join(f"{k}: {v}" for k, v in p.value_sources.items()) + ")")
        st.dataframe(show, hide_index=True, width="stretch")
    else:
        st.error("The data has blocking errors and cannot be loaded. Correct them and the check will rerun. "
                 "The project currently shown in the dashboard has not been changed.")


def confirm_and_load(p: ProcessedData, label: str, key: str, replace_name: Optional[str] = None):
    """On the home screen (nothing loaded) open directly; otherwise ask before replacing the shown project."""
    ok = replace_name is None or st.checkbox(f"Replace the project currently shown (“{replace_name}”) with this data",
                                             key=f"{key}_conf")
    if st.button("Open dashboard" if replace_name is None else "Load into dashboard", type="primary",
                 disabled=not ok, key=f"{key}_btn"):
        st.session_state.current = make_current(p, label)
        st.session_state.flash = f"Loaded “{p.settings.name}” ({MODES[p.mode]}, {len(p.periods)} reporting dates)."
        st.rerun()


def results_export(r: pd.DataFrame) -> pd.DataFrame:
    keep = [c for c in r.columns if not c.endswith("__note")]
    return r[keep]


def excel_export(cur: dict, r: pd.DataFrame) -> bytes:
    p = cur["processed"]
    s = p.settings
    info = pd.DataFrame({"Item": ["Project name", "Project type", "Currency", "BAC", "Baseline start",
                                  "Baseline completion", "Input mode", "Value sources", "Independent ETC entries",
                                  "Exported"],
                         "Value": [s.name, s.project_type, s.currency, p.bac, s.baseline_start, s.baseline_finish,
                                   MODES[p.mode], "; ".join(f"{k}: {v}" for k, v in p.value_sources.items()),
                                   "; ".join(f"{pd.Timestamp(k).date()}: {v:,.2f} (user-entered)"
                                             for k, v in cur["etc_overrides"].items()) or "none",
                                   datetime.now().strftime("%Y-%m-%d %H:%M")]})
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        info.to_excel(xw, sheet_name="Project", index=False)
        p.inputs.to_excel(xw, sheet_name="Validated inputs", index=False)
        p.periods.to_excel(xw, sheet_name="Reporting periods", index=False)
        r.to_excel(xw, sheet_name="EVM results", index=False)
        if p.wp_detail is not None:
            p.wp_detail.to_excel(xw, sheet_name="Work packages", index=False)
        p.report.to_frame().to_excel(xw, sheet_name="Validation", index=False)
    return bio.getvalue()


CONF_ICON = {"High": "🟢 High", "Medium": "🟡 Medium", "Low": "🟠 Low"}


def smart_upload(up, replace_name):
    """Upload flow: the smart reader understands the file, the user checks it, then normal validation."""
    data = up.getvalue()
    fid = f"{up.name}_{len(data)}"
    sheet = None
    try:
        if up.name.lower().endswith(".xlsx"):
            names = excel_sheet_names(data)
            if len(names) > 1:
                pick = st.selectbox("Worksheet", ["Detect automatically"] + names, key=f"sheet_{fid}")
                sheet = None if pick == "Detect automatically" else pick
        detected = understand(data, up.name, sheet=sheet)
    except Exception as exc:  # unreadable file: report, never crash or replace the project
        st.error(f"The file could not be read: {exc}. Check that it is a valid CSV or XLSX file.")
        return

    st.markdown("**3. What the smart reader understood**")
    modes = list(MODES)
    up_mode = st.selectbox("Data type (detected from your columns — change it if it is wrong)", modes,
                           index=modes.index(detected.mode), format_func=lambda m: MODES[m], key=f"upmode_{fid}")
    u = detected if up_mode == detected.mode else understand(data, up.name, mode=up_mode, sheet=sheet)
    with st.container(border=True):
        facts = [f"**{MODES[u.mode]}** — {u.mode_reason}",
                 f"{len(u.table)} data rows, header on row {u.header_row}" + (f" of sheet '{u.sheet}'" if u.sheet else "")]
        if "status_date" in u.metadata:
            facts.append(f"Status date found above the table: **{u.metadata['status_date']:%d %b %Y}**")
        st.markdown("\n".join(f"- {x}" for x in facts))
        if u.fixes:
            st.markdown("**Fixed automatically** (shown so you can check them):\n" +
                        "\n".join(f"- ✅ {x}" for x in u.fixes))
        for h in u.hints:
            st.info(h)
        mt = pd.DataFrame([{"Dashboard field": FIELDS[m["field"]][0], "Your column": m["column"],
                            "Confidence": CONF_ICON[m["confidence"]], "Why": m["reason"]} for m in u.matches])
        if len(mt):
            st.dataframe(mt, hide_index=True, width="stretch")
        if u.unused_columns:
            st.caption("Not used (not needed or not recognised — never guessed): " +
                       ", ".join(f"'{c}'" for c in u.unused_columns))

    # ---- anything still missing: let the user supply it here or in the file
    if u.missing:
        names_ = ", ".join(entry_label(f) for f in u.missing)
        st.warning(f"Your file does not contain: **{names_}**. Add it below, or download your file with the "
                   "missing column added, fill it in and upload it again.")
        for f in list(u.missing):
            if f == "reporting_date":
                d = st.date_input("Status date of this file (the date all values refer to)", value=None,
                                  key=f"entry_date_{fid}")
                if d:
                    t = values_entry_table(u, f)
                    t[entry_label(f)] = pd.Timestamp(d)
                    u = with_entered_values(u, f, t)
                continue
            st.markdown(f"**Enter {entry_label(f).lower()}**" + (" for each activity" if u.mode == "work_package"
                                                                   else " for each reporting date"))
            t = values_entry_table(u, f)
            cfg = {c: st.column_config.Column(disabled=True) for c in t.columns if c != entry_label(f)}
            cfg[entry_label(f)] = st.column_config.NumberColumn(entry_label(f), min_value=0.0, format="%.2f",
                                                                help=FIELDS[f][1])
            edited = st.data_editor(t, column_config=cfg, hide_index=True, width="stretch", key=f"entry_{f}_{fid}",
                                    height=min(35 * (len(t) + 1) + 3, 735))      # all rows visible up to 20
            u = with_entered_values(u, f, edited)
        st.download_button("Download my file with the missing column(s) added (Excel)",
                           workbook_with_missing_columns(u), file_name=f"{Path(up.name).stem}_to_fill.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=f"dl_fill_{fid}")

    raw = u.table
    spec = MODE_FIELDS[up_mode]
    opts = ["— not mapped —"] + list(raw.columns)
    mapping = dict(u.mapping)
    with st.expander("Check or change the column mapping", expanded=False):
        st.caption("Pre-filled by the smart reader. Fields marked * are required. Columns you do not map are "
                   "ignored, never guessed.")
        grid = st.columns(3)
        for i, f in enumerate(mode_fields(up_mode)):
            lab = FIELDS[f][0] + (" *" if f in spec["required"] else "")
            if spec["ac_choice"] and f in ("ac_cumulative", "ac_period"):
                lab += " (one of the two AC fields required)"
            cur_ = mapping.get(f)
            choice = grid[i % 3].selectbox(lab, opts, index=opts.index(cur_) if cur_ in opts else 0,
                                           key=f"map_{up_mode}_{f}_{fid}_{cur_}", help=FIELDS[f][1])
            mapping[f] = None if choice == opts[0] else choice
    with st.expander(f"Preview of the cleaned data ({len(raw)} rows)"):
        st.dataframe(raw.head(50), hide_index=True, width="stretch")

    st.markdown("**4. Project settings**")
    bac_file = None
    if mapping.get("bac"):
        vals = {to for to in pd.to_numeric(raw[mapping["bac"]].astype(str).str.replace(",", ""),
                                           errors="coerce").dropna()}
        bac_file = sorted(vals)[0] if len(vals) == 1 else None
    base = ProjectSettings()
    if mapping.get("project_name"):
        nm = [v for v in raw[mapping["project_name"]] if not is_missing(v)]
        base.name = str(nm[0]).strip() if nm else ""
    elif u.metadata.get("project_name"):
        base.name = str(u.metadata["project_name"])
    settings = settings_form(f"up_{up_mode}_{fid}", base, up_mode, bac_file)
    st.markdown("**5. Validation result**")
    p = prepare(raw, mapping, settings, up_mode)
    show_validation(p)
    if p.ok:
        confirm_and_load(p, f"Uploaded file: {up.name}", "up", replace_name)


def data_loader(on_home: bool):
    """Upload / manual entry / built-in example. Used on the home screen and in the Data tab."""
    cur_ = st.session_state.get("current")
    cur_proc: Optional[ProcessedData] = None if on_home or cur_ is None else cur_["processed"]
    replace_name = None if cur_proc is None else cur_proc.settings.name
    st.subheader("Start a project" if on_home else "Load or enter project data")
    mode = st.radio("1. What kind of data do you have?", list(MODES), format_func=lambda m: MODES[m],
                    horizontal=True, key="data_mode")
    st.caption({
        "progress": "You supply BAC, cumulative planned %, cumulative actual PHYSICAL % and actual cost. The tool "
                    "derives PV = planned % × BAC and EV = actual % × BAC.",
        "precalc": "You supply cumulative PV, EV and AC (e.g. exported from project-controls software). They are "
                   "used exactly as supplied; the tool calculates the remaining metrics.",
        "work_package": "You supply each work package's budget, cumulative planned and actual % and cumulative AC at "
                        "every reporting date. The tool sums budget-weighted PV and EV across work packages.",
    }[mode])
    tc = st.columns(4)
    tbuf = io.StringIO()
    template(mode).to_csv(tbuf, index=False)
    tc[0].download_button(f"Template — {MODES[mode]} (CSV)", tbuf.getvalue(), f"template_{mode}.csv", "text/csv")
    sample_file = {"progress": "sample_project_progress.csv", "precalc": "sample_project_evm.csv",
                   "work_package": "sample_project_work_packages.csv"}[mode]
    tc[1].download_button("Sample dataset (CSV)", (DATA / sample_file).read_bytes(), sample_file, "text/csv")
    tc[2].download_button("Sample dataset, all formats (Excel)", (DATA / "sample_project.xlsx").read_bytes(),
                          "sample_project.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    tc[3].download_button("Benchmark case (CSV)", (DATA / "benchmark_case_work_packages.csv").read_bytes(),
                          "benchmark_case_work_packages.csv", "text/csv")

    how = st.radio("2. How do you want to provide it?", ["Upload a file", "Enter or edit manually",
                                                          "Load a built-in example"], horizontal=True, key="how")

    if how == "Upload a file":
        up = st.file_uploader("Upload a CSV or Excel (.xlsx) file", type=["csv", "xlsx"], key="uploader",
                              help="Any layout is fine: the smart reader finds the header row, the columns, the "
                                   "data type and a status date written above the table.")
        if up is not None:
            smart_upload(up, replace_name)

    elif how == "Enter or edit manually":
        same = cur_proc is not None and cur_proc.mode == mode
        st.caption("Edit cells directly; use the + row control to add reporting periods. Values are checked with "
                   "the same rules as uploaded files before anything is applied.")
        bkey = f"manual_base_{mode}"
        if bkey not in st.session_state:
            if same:
                cols = [c_ for c_ in mode_fields(mode) if c_ in cur_proc.inputs.columns and c_ not in
                        ("project_name", "currency", "bac")]
                st.session_state[bkey] = cur_proc.inputs[cols].copy()
            else:
                st.session_state[bkey] = template(mode)
        cc = st.columns([2, 2, 3])
        if cc[0].button("Reload from current project", disabled=not same):
            st.session_state.pop(bkey, None)
            st.session_state.pop(f"editor_{mode}", None)
            st.rerun()
        wipe = cc[2].checkbox("I want to discard the table and start blank", key=f"wipe_{mode}")
        if cc[1].button("Start a new blank table", disabled=not wipe):
            st.session_state[bkey] = template(mode).iloc[0:0]
            st.session_state.pop(f"editor_{mode}", None)
            st.rerun()
        base_df = st.session_state[bkey].copy()
        fields = [f for f in mode_fields(mode) if f not in ("project_name", "currency", "bac")]
        for f in fields:
            if f not in base_df.columns:
                base_df[f] = None
        base_df = base_df[fields]
        base_df["reporting_date"] = pd.to_datetime(base_df["reporting_date"], errors="coerce")
        for f in fields:
            if FIELDS[f][2] in ("money", "pct"):
                base_df[f] = pd.to_numeric(base_df[f], errors="coerce")
            elif FIELDS[f][2] == "text":
                base_df[f] = base_df[f].astype("object").where(base_df[f].notna(), None)
        cfg = {}
        for f in fields:
            lab, desc, kind = FIELDS[f]
            req = f in MODE_FIELDS[mode]["required"]
            lab = lab + (" *" if req else "")
            if kind == "date":
                cfg[f] = st.column_config.DateColumn(lab, help=desc, format="YYYY-MM-DD")
            elif kind == "pct":
                cfg[f] = st.column_config.NumberColumn(lab, help=desc + " (0–100)", format="%.2f")
            elif kind == "money":
                cfg[f] = st.column_config.NumberColumn(lab, help=desc, format="%.2f")
            else:
                cfg[f] = st.column_config.TextColumn(lab, help=desc)
        edited = st.data_editor(base_df, num_rows="dynamic", column_config=cfg, key=f"editor_{mode}",
                                width="stretch", hide_index=True)
        st.markdown("**Project settings**")
        settings = settings_form(f"man_{mode}", cur_proc.settings if same else ProjectSettings(), mode)
        st.markdown("**Validation result**")
        p = prepare(edited, {c_: c_ for c_ in edited.columns}, settings, mode, first_data_row=1)
        st.caption("Row numbers in messages count from 1 = first table row.")
        show_validation(p)
        if p.ok:
            confirm_and_load(p, "Manually entered data", "man", replace_name)

    else:
        st.caption("The demo and benchmark use SYNTHETIC data. The real project is an actual Belgian apartment "
                   "building from the DSLIB empirical project database (Ghent University): 25 activities, "
                   "13 tracking periods, values in EUR. Source: Batselier & Vanhoucke (2015), International "
                   "Journal of Project Management 33(3), 697–710.")
        ex = st.radio("Example", ["Demo project — G+7 commercial building, 6 work packages, 9 months",
                                  "Benchmark case — G+4 residential block, 4 work packages, 2 months "
                                  "(used for manual validation)",
                                  "Real project — apartment building, Belgium 2011–12 (DSLIB C2014-05)"],
                      key="example")
        ok = on_home or st.checkbox(f"Replace the project currently shown (“{replace_name}”)", key="ex_conf")
        if st.button("Open example" if on_home else "Load example", type="primary", disabled=not ok):
            st.session_state.current = (demo_project() if ex.startswith("Demo") else
                                        real_project() if ex.startswith("Real") else benchmark_project())
            st.session_state.flash = "Example loaded."
            st.rerun()



def home_screen():
    with st.sidebar:
        st.markdown("### EVM Dashboard")
        st.caption(f"CE 725 course project · v{__version__}")
        st.caption("Start a project on the home screen. The analysis opens once data is loaded.")
    st.markdown('<div class="hero"><div class="hero-title">EVM Dashboard</div>'
                '<div class="hero-sub">Earned Value Management for construction projects: compare planned '
                'progress, earned value and actual cost, spot problems early and forecast the final cost.</div>'
                '</div>', unsafe_allow_html=True)
    data_loader(on_home=True)
    st.divider()
    st.markdown("**Or open an example project in one click**")
    q = st.columns(3)
    for col, key, lab, fn in ((q[0], "home_demo", "Demo project (synthetic, 6 work packages)", demo_project),
                              (q[1], "home_real", "Real project (DSLIB C2014-05, Belgium)", real_project),
                              (q[2], "home_bench", "Benchmark case (manual validation)", benchmark_project)):
        if col.button(lab, key=key, width="stretch"):
            st.session_state.current = fn()
            st.rerun()

# ---------------------------------------------------------------- main flow
if "current" not in st.session_state:
    home_screen()
    st.stop()

cur = st.session_state.current
proc: ProcessedData = cur["processed"]
S: ProjectSettings = proc.settings
res = current_results(cur)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### EVM Dashboard")
    st.caption(f"CE 725 course project · v{__version__}")
    if st.button("← Home: start another project", key="go_home", width="stretch"):
        del st.session_state["current"]
        st.rerun()
    method = st.selectbox("Forecasting method (EAC)", list(METHODS), index=0,
                          format_func=lambda k: f"{k[0]} — {METHODS[k]['short']}",
                          help="Each method makes a different assumption about future performance. "
                               "See the Forecasts tab to compare them.")
    st.caption(METHODS[method]["assumption"])
    unit = st.selectbox("Show money in", ["units", "lakh", "crore", "million"],
                        index=1 if S.currency == "INR" else 0,
                        format_func=lambda u: {"units": f"{S.currency} (full)", "lakh": f"{S.currency} lakh",
                                               "crore": f"{S.currency} crore", "million": f"{S.currency} million"}[u],
                        help="Display only. Calculations always use full precision.")
    dates = list(res["reporting_date"])
    sel_i = st.selectbox("Reporting date", range(len(dates)), index=len(dates) - 1,
                         format_func=lambda i: pd.Timestamp(dates[i]).strftime("%d %b %Y"))
    with st.expander("Health screening thresholds"):
        st.caption("Team-chosen screening rules, not industry standards. Adjust to your organisation's policy.")
        warn = st.number_input("CPI/SPI warning below", 0.5, 1.5, 1.00, 0.01)
        crit = st.number_input("CPI/SPI critical below", 0.5, 1.5, 0.90, 0.01)
        ow = st.number_input("Forecast overrun warning above (%)", -50.0, 100.0, 0.0, 0.5)
        oc = st.number_input("Forecast overrun critical above (%)", -50.0, 200.0, 10.0, 0.5)
        tg = st.number_input("TCPI − CPI gap flagged as 'BAC unlikely'", 0.0, 1.0, 0.10, 0.01)
        if crit > warn or ow > oc:
            st.error("Critical thresholds must be stricter than warning thresholds.")
    th = HealthThresholds(warn, crit, ow, oc, tg)
    st.divider()
    st.caption(f"Loaded: {cur['label']}")
    st.caption(f"Input mode: {MODES[proc.mode]}")

row = res.iloc[sel_i]
sel_date = row["reporting_date"]
money = lambda v: format_money(v, S.currency, unit)  # noqa: E731
M = lambda name: metric_from_row(row, name)  # noqa: E731
health = classify(row, method, th)
state_cls = {FAVOURABLE: "Favourable", WARNING: "Warning", CRITICAL: "Critical", INSUFFICIENT: "Insufficient"}

# ---------------------------------------------------------------- signboard
st.markdown(f"""
<div class="signboard sb-{state_cls[health['overall']]}">
  <div class="sb-state">{health['overall']}</div>
  <div class="sb-body">
    <div class="sb-title">{S.name}</div>
    <div class="sb-meta">Status date {pd.Timestamp(sel_date).strftime('%d %b %Y')} &nbsp;|&nbsp;
      {S.project_type} &nbsp;|&nbsp; Forecast method {method[0]}: {METHODS[method]['short']}</div>
  </div>
</div>""", unsafe_allow_html=True)
if cur["label"].startswith("REAL"):
    st.markdown('<div class="demo-note">Real project data from the DSLIB empirical project database '
                '(Batselier &amp; Vanhoucke, 2015), values in EUR. Results reproduce the EVM values recorded '
                'in ProTrack for every tracking period.</div>', unsafe_allow_html=True)
elif "synthetic" in cur["label"].lower():
    st.markdown('<div class="demo-note">You are viewing an illustrative project built from synthetic data. '
                'Load your own data from <b>Home</b> (sidebar) or the <b>Data</b> tab.</div>', unsafe_allow_html=True)

t_over, t_trend, t_fc, t_comm, t_data = st.tabs(["Overview", "Trends", "Forecasts", "Commentary", "Data"])


def kpi(col, label, name, kind, key=None, delta=None, delta_color="normal"):
    m = M(name)
    col.metric(label, format_metric(m, kind, S.currency, unit), delta=delta, delta_color=delta_color,
               help=KPI_HELP.get(key or name, "") + (f"\n\nNote: {m.note}" if m.note else ""), border=True)



STATUS_STYLE = {FAVOURABLE: "background-color:#E3F1E8;color:#1E5C38", WARNING: "background-color:#FFF4D6;color:#6B4A00",
                CRITICAL: "background-color:#FBE4E2;color:#8A1C16", NOT_STARTED: "color:#6B7280",
                INSUFFICIENT: "color:#6B7280"}


def _style_status(v):
    return STATUS_STYLE.get(v, "")


def _style_negative(v):
    return "color:#8A1C16" if isinstance(v, str) and v.startswith("-") else ""


def _style_low_index(v):
    try:
        return "color:#8A1C16;font-weight:600" if float(v) < th.index_critical_below else ""
    except ValueError:
        return ""


def performance_panel():
    """S-curve + combined CPI/SPI trend, then work-package status + top problem activities."""
    with st.container(border=True):
        st.subheader("Performance and problem areas")
        freq_ = S.reporting_frequency
        a, b = st.columns([1.35, 1])
        a.plotly_chart(cumulative_chart(res, proc.bac, method, S.currency, unit, freq_, sel_date, S.baseline_finish),
                       width="stretch", key="ov_cum")
        b.plotly_chart(combined_index_chart(res, freq_, th.index_warning_below, th.index_critical_below),
                       width="stretch", key="ov_idx")
        if proc.wp_detail is None:
            st.info("Work-package status and top problem activities need work-package data (input type "
                    f"'{MODES['work_package']}'). This project was loaded as project-level data.")
            return
        a, b = st.columns([1, 1.15])
        wps = work_package_status(proc.wp_detail, sel_date, th)
        label = (wps["activity_id"] + " " + wps["activity_name"]).str.strip()
        idx = lambda v, s_: "–" if s_ == NOT_STARTED else format_index(v)  # noqa: E731
        view = pd.DataFrame({"Work package": label,
                             "CPI": [idx(v, s_) for v, s_ in zip(wps["cpi"], wps["status"])],
                             "SPI": [idx(v, s_) for v, s_ in zip(wps["spi"], wps["status"])],
                             "Status": wps["status"]})
        with a:
            st.markdown("**Work package status**")
            st.dataframe(view.style.map(_style_status, subset=["Status"])
                         .map(_style_low_index, subset=["CPI", "SPI"]), hide_index=True, width="stretch")
        top = problem_activities(proc.wp_detail, sel_date, n=5)
        with b:
            st.markdown("**Top problem activities**")
            if top.empty:
                st.success("No work package is over budget or behind schedule at this date.")
            else:
                tv = pd.DataFrame({"Activity": (top["activity_id"] + " " + top["activity_name"]).str.strip(),
                                   "Main issue": top["main_issue"],
                                   "CV": [money(v) for v in top["cv"]], "SV": [money(v) for v in top["sv"]]})
                st.dataframe(tv.style.map(_style_negative, subset=["CV", "SV"]), hide_index=True, width="stretch")
        st.caption(f"Status per work package uses the sidebar thresholds (Warning below "
                   f"{th.index_warning_below:.2f}, Critical below {th.index_critical_below:.2f}, worst of CPI and "
                   "SPI). Problems are ranked by the more negative of CV and SV.")

# ================================================================ OVERVIEW
with t_over:
    st.subheader("Where the project stands")
    st.markdown(f'<p class="section-intro">All values are cumulative to {pd.Timestamp(sel_date).strftime("%d %b %Y")}. '
                'Hover over the ⓘ beside each figure for its definition.</p>', unsafe_allow_html=True)
    c = st.columns(4)
    kpi(c[0], "Budget at completion (BAC)", "bac", "money")
    kpi(c[1], "Planned progress", "pct_planned", "pct", "pct")
    kpi(c[2], "Earned (physical) progress", "pct_complete", "pct", "pct")
    kpi(c[3], "Budget spent", "pct_spent", "pct", "pct")
    c = st.columns(4)
    kpi(c[0], "Planned value (PV)", "pv", "money")
    kpi(c[1], "Earned value (EV)", "ev", "money")
    kpi(c[2], "Actual cost (AC)", "ac", "money")
    kpi(c[3], "Cost variance (CV)", "cv", "money")
    c = st.columns(4)
    kpi(c[0], "Schedule variance (SV)", "sv", "money")
    cpi, spi = M("cpi"), M("spi")
    kpi(c[1], "CPI (cost efficiency)", "cpi", "index",
        delta=f"{cpi.value - 1:+.3f} vs 1.00" if cpi.available else None)
    kpi(c[2], "SPI (schedule efficiency)", "spi", "index",
        delta=f"{spi.value - 1:+.3f} vs 1.00" if spi.available else None)
    kpi(c[3], "TCPI to finish within BAC", "tcpi_bac", "index")
    st.markdown(f"**Forecast — method {method[0]}** ({METHODS[method]['formula']})")
    c = st.columns(4)
    ovp = M(f"overrun_pct_{method}")
    kpi(c[0], "Estimate at completion (EAC)", f"eac_{method}", "money", "eac",
        delta=f"{ovp.value:+.2f}% vs BAC" if ovp.available else None, delta_color="inverse")
    kpi(c[1], "Estimate to complete (ETC)", f"etc_{method}", "money", "etc")
    kpi(c[2], "Forecast overrun", f"overrun_{method}", "money", "overrun")
    kpi(c[3], "TCPI to reach this EAC", f"tcpi_eac_{method}", "index", "tcpi_eac")

    performance_panel()

    st.markdown("#### Health screening")
    hdf = pd.DataFrame(health["components"])
    st.dataframe(hdf, hide_index=True, width="stretch")
    st.caption("Overall label: Critical if any indicator is critical; otherwise 'Insufficient data' if any "
               "indicator cannot be calculated; otherwise the worst of Warning/Favourable. Missing indices never "
               "make a project look healthy.")
    tb = M("tcpi_bac")
    if not tb.available:
        st.info(f"TCPI to BAC: {tb.note}")
    ac_m, bac_m = M("ac"), M("bac")
    if ac_m.available and ac_m.value > bac_m.value:
        st.error(f"Actual cost already exceeds BAC by {money(ac_m.value - bac_m.value)} — an overrun already incurred.")
    src = proc.value_sources
    st.caption("Value sources: " + "; ".join(f"{k.upper()} {v}" for k, v in src.items() if k in ("pv", "ev", "ac")))
    nw = len(proc.report.warnings)
    if nw:
        st.warning(f"{nw} data warning(s) were raised when this project was loaded. Review them in the Data tab.")

# ================================================================ TRENDS
with t_trend:
    freq = S.reporting_frequency
    st.plotly_chart(cumulative_chart(res, proc.bac, method, S.currency, unit, freq, sel_date, S.baseline_finish),
                    width="stretch", key="tr_cum")
    st.caption("Solid lines: observed values. Dashed line: forecast EAC under the selected method. "
               "Missing reporting periods appear as breaks, not as connected lines.")
    st.plotly_chart(combined_index_chart(res, freq, th.index_warning_below, th.index_critical_below),
                    width="stretch", key="tr_idx")
    a, b = st.columns(2)
    a.plotly_chart(progress_chart(proc.periods, freq), width="stretch")
    b.plotly_chart(budget_vs_forecast_chart(row, proc.bac, S.currency, unit), width="stretch")
    if proc.wp_detail is not None:
        fig = wp_variance_chart(proc.wp_detail, sel_date, S.currency, unit)
        if fig:
            st.plotly_chart(fig, width="stretch")
    with st.expander("Period-by-period table"):
        cols = ["reporting_date", "pv", "ev", "ac", "cv", "sv", "cpi", "spi", "tcpi_bac", f"eac_{method}"]
        tbl = res[cols].copy()
        disp = pd.DataFrame({"Reporting date": tbl["reporting_date"].dt.strftime("%d %b %Y")})
        for c_ in cols[1:]:
            kind = "index" if c_ in ("cpi", "spi", "tcpi_bac") else "money"
            disp[c_.upper().replace(f"_{method}", f" ({method[0]})")] = [
                format_metric(metric_from_row(r, c_), kind, S.currency, unit) for _, r in res.iterrows()]
        st.dataframe(disp, hide_index=True, width="stretch")

# ================================================================ FORECASTS
with t_fc:
    st.subheader("Forecast scenarios")
    st.markdown('<p class="section-intro">Each method answers "what will the project cost at completion?" under a '
                'different assumption about future performance. None is a guaranteed outcome; the spread between '
                'them is itself useful information.</p>', unsafe_allow_html=True)
    rows_ = []
    for m, meta in METHODS.items():
        gm = lambda n: metric_from_row(row, f"{n}_{m}")  # noqa: E731
        e = gm("eac")
        rows_.append({"Method": meta["label"], "Formula": meta["formula"],
                      "EAC": format_metric(e, "money", S.currency, unit),
                      "ETC": format_metric(gm("etc"), "money", S.currency, unit),
                      "VAC": format_metric(gm("vac"), "money", S.currency, unit),
                      "Overrun": format_metric(gm("overrun"), "money", S.currency, unit),
                      "Overrun %": format_metric(gm("overrun_pct"), "pct"),
                      "TCPI to EAC": format_metric(gm("tcpi_eac"), "index"),
                      "Status / note": e.note or ("Selected" if m == method else "")})
    st.dataframe(pd.DataFrame(rows_), hide_index=True, width="stretch")
    with st.expander("Assumptions behind each method"):
        for m, meta in METHODS.items():
            st.markdown(f"**{meta['label']}** — `{meta['formula']}`  \n{meta['assumption']}")
        st.markdown("**Useful identities for checking:** TCPI to the BAC/CPI forecast always equals CPI; "
                    "TCPI to the budget-rate forecast always equals 1.00; TCPI to the CPI×SPI forecast equals "
                    "CPI × SPI.")
    a, b = st.columns([1, 1])
    a.plotly_chart(budget_vs_forecast_chart(row, proc.bac, S.currency, unit), width="stretch", key="bvf2")
    b.plotly_chart(eac_trend_chart(res, proc.bac, S.currency, unit, S.reporting_frequency), width="stretch")

    st.markdown("#### Independent estimate (method D)")
    st.caption("Enter a bottom-up estimate of the cost to complete the remaining work, prepared by the project "
               f"team, for {pd.Timestamp(sel_date).strftime('%d %b %Y')}. It applies to this session only and is "
               "included in exports, labelled as user-entered.")
    file_etc = proc.periods.loc[proc.periods["reporting_date"] == sel_date, "independent_etc"]
    existing = cur["etc_overrides"].get(sel_date, file_etc.iloc[0] if len(file_etc) else None)
    c1, c2, c3 = st.columns([2, 1, 1])
    val = c1.number_input(f"Independent ETC ({S.currency}, full amount)", min_value=0.0, step=100000.0,
                          value=float(existing) if existing is not None and not is_missing(existing) else None,
                          key=f"etc_in_{sel_i}")
    if c2.button("Apply estimate", disabled=val is None):
        cur["etc_overrides"][sel_date] = float(val)
        st.rerun()
    if c3.button("Clear estimate", disabled=sel_date not in cur["etc_overrides"]):
        cur["etc_overrides"].pop(sel_date, None)
        st.rerun()

# ================================================================ COMMENTARY
with t_comm:
    st.subheader(f"Progress commentary — {pd.Timestamp(sel_date).strftime('%d %B %Y')}")
    st.markdown('<p class="section-intro">Generated by transparent rules from the calculated metrics (no AI service, '
                'works offline). It states what the numbers show and where to look; it does not claim causes the '
                'data cannot show.</p>', unsafe_allow_html=True)
    note = proc.periods.loc[proc.periods["reporting_date"] == sel_date, "notes"]
    note = note.iloc[0] if len(note) and isinstance(note.iloc[0], str) and note.iloc[0].strip() else None
    comm = generate_commentary(res, sel_i, method, th, S.currency, unit, proc.wp_detail, note, S.baseline_finish)
    md = [f"# Progress commentary — {S.name}", f"Status date: {pd.Timestamp(sel_date).date()}  ",
          f"Health (screening): **{health['overall']}**  ", f"Forecast method: {METHODS[method]['label']}", ""]
    for sec, items in comm.items():
        if not items:
            continue
        st.markdown(f"#### {sec}")
        st.markdown("\n".join(f"- {x}" for x in items))
        md += [f"## {sec}", *[f"- {x}" for x in items], ""]
    md.append(f"_Generated by the CE 725 EVM Dashboard v{__version__} on {datetime.now():%Y-%m-%d %H:%M}. "
              "Figures are only as reliable as the input data._")
    st.download_button("Download commentary (Markdown)", "\n".join(md),
                       file_name=f"evm_commentary_{pd.Timestamp(sel_date).date()}.md", mime="text/markdown")


# ================================================================ DATA
with t_data:
    if st.session_state.get("flash"):
        st.success(st.session_state.pop("flash"))
    st.subheader("Current project")
    c = st.columns([3, 1, 1, 1])
    c[0].markdown(f"**{S.name}** — {MODES[proc.mode]}, {len(proc.periods)} reporting dates, BAC "
                  f"{format_money(proc.bac, S.currency)}  \n{cur['label']}")
    stamp = pd.Timestamp(sel_date).date()
    c[1].download_button("Results (CSV)", results_export(res).to_csv(index=False), f"evm_results_{stamp}.csv",
                         "text/csv")
    c[2].download_button("Inputs (CSV)", proc.inputs.to_csv(index=False), "evm_validated_inputs.csv",
                         "text/csv")
    c[3].download_button("Workbook (Excel)", excel_export(cur, res), f"evm_project_{stamp}.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if proc.report.issues:
        with st.expander(f"Validation messages for the current project ({len(proc.report.warnings)} warning(s))"):
            st.dataframe(proc.report.to_frame(), hide_index=True, width="stretch")

    st.divider()
    data_loader(on_home=False)

st.markdown("---")
st.caption("CE 725 Construction Economics and Finance — EVM Dashboard. Forecasts are assumption-based estimates, "
           "not guarantees. Health labels are configurable screening rules and do not replace professional "
           "judgement. Data you upload stays on the machine running this app.")
