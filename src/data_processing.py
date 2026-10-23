"""
Input pipeline shared by file upload and manual entry.

    raw table -> column mapping -> parse -> validate -> derive PV/EV/AC -> periods table

Three input modes:
  progress      Progress-Based Project Data: BAC, cumulative planned %, cumulative
                actual PHYSICAL %, actual cost. PV = planned% x BAC, EV = actual% x BAC.
  precalc       Pre-calculated EVM Data: cumulative PV, EV, AC supplied directly and
                used as supplied (never overwritten from percentages).
  work_package  Work-package data: budget and progress per activity per date.
                PV = sum(budget_i x planned%_i), EV = sum(budget_i x actual%_i),
                AC = sum(AC_i). Budget-weighted, never an unweighted average of %s.

Every cumulative series is cumulative; period costs are only summed when no
cumulative AC is supplied.  Supplied/derived status is recorded per value.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .validation import (MONEY_TOL, ValidationReport, check_dates_in_baseline, check_non_decreasing,
                         check_percent_range, check_reporting_gaps, is_missing, to_date, to_number)

MODES = {
    "progress": "Progress-Based Project Data",
    "precalc": "Pre-calculated EVM Data",
    "work_package": "Work-Package-Level Data",
}

# Canonical fields: (label, description, kind)
FIELDS: Dict[str, Tuple[str, str, str]] = {
    "reporting_date": ("Reporting date", "Status date the cumulative values refer to", "date"),
    "planned_progress_pct": ("Planned progress % (cumulative)", "Baseline % of budgeted scope planned by the date", "pct"),
    "actual_progress_pct": ("Actual physical progress % (cumulative)", "% of budgeted scope physically completed", "pct"),
    "pv_cumulative": ("PV (cumulative)", "Planned Value to date", "money"),
    "ev_cumulative": ("EV (cumulative)", "Earned Value to date", "money"),
    "ac_cumulative": ("AC (cumulative)", "Actual Cost to date", "money"),
    "ac_period": ("AC this period", "Actual cost incurred in this reporting period only", "money"),
    "bac": ("BAC", "Budget at Completion (constant)", "money"),
    "independent_etc": ("Independent ETC", "Bottom-up estimate of remaining cost (optional)", "money"),
    "activity_id": ("Activity / WP ID", "Work-package identifier", "text"),
    "activity_name": ("Activity / WP name", "Work-package description", "text"),
    "activity_budget": ("Activity budget", "Approved budget of the work package", "money"),
    "notes": ("Notes", "Free-text explanation", "text"),
    "project_name": ("Project name", "Optional; constant", "text"),
    "currency": ("Currency", "Optional; constant", "text"),
}

MODE_FIELDS = {
    "progress": {"required": ["reporting_date", "planned_progress_pct", "actual_progress_pct"],
                 "ac_choice": True,
                 "optional": ["bac", "independent_etc", "notes", "project_name", "currency"]},
    "precalc": {"required": ["reporting_date", "pv_cumulative", "ev_cumulative"],
                "ac_choice": True,
                "optional": ["bac", "independent_etc", "notes", "project_name", "currency"]},
    "work_package": {"required": ["reporting_date", "activity_id", "activity_budget", "planned_progress_pct",
                                  "actual_progress_pct", "ac_cumulative"],
                     "ac_choice": False,
                     "optional": ["activity_name", "notes", "project_name", "currency"]},
}

# Alternative header names (normalised). Deliberately excludes MS Project's bare
# "% Complete", which is DURATION-based, not physical progress: map it manually only
# if you are sure it measures physical work.
SYNONYMS = {
    "reporting_date": ["date", "report_date", "status_date", "data_date", "as_of_date", "period_end",
                       "reporting_period_end", "period_ending"],
    "planned_progress_pct": ["planned_pct", "planned_progress", "planned_percent_complete", "plan_pct",
                             "planned_cumulative_progress", "baseline_progress", "scheduled_progress",
                             "planned_progress_cumulative", "planned_progress_percent"],
    "actual_progress_pct": ["actual_pct", "actual_progress", "actual_physical_progress", "physical_progress",
                            "physical_percent_complete", "actual_percent_complete", "actual_progress_cumulative",
                            "actual_progress_percent"],
    "pv_cumulative": ["pv", "planned_value", "bcws", "cumulative_pv", "pv_cum", "cum_pv"],
    "ev_cumulative": ["ev", "earned_value", "bcwp", "cumulative_ev", "ev_cum", "cum_ev"],
    "ac_cumulative": ["ac", "actual_cost", "acwp", "cumulative_ac", "ac_cum", "cum_ac", "cumulative_actual_cost",
                      "actual_cost_cumulative"],
    "ac_period": ["period_cost", "actual_cost_period", "period_actual_cost", "cost_this_period", "monthly_cost",
                  "ac_this_period"],
    "bac": ["budget_at_completion", "total_budget", "project_budget"],
    "independent_etc": ["etc_independent", "bottom_up_etc", "manual_etc", "etc"],
    "activity_id": ["wp_id", "work_package_id", "task_id", "activity_code", "wbs", "wbs_code", "id"],
    "activity_name": ["wp_name", "work_package", "work_package_name", "task_name", "activity", "description"],
    "activity_budget": ["wp_budget", "work_package_budget", "task_budget", "activity_bac", "budgeted_cost"],
    "notes": ["note", "remarks", "comments", "comment"],
    "project_name": ["project", "project_title"],
    "currency": ["curr"],
}


@dataclass
class ProjectSettings:
    name: str = ""
    project_type: str = "Building"
    currency: str = "INR"
    bac: Optional[float] = None
    baseline_start: Optional[date] = None
    baseline_finish: Optional[date] = None
    project_manager: str = ""
    notes: str = ""
    reporting_frequency: str = "Monthly"   # Monthly | Weekly | Irregular
    dayfirst: bool = True                   # DD/MM/YYYY for non-ISO dates


@dataclass
class ProcessedData:
    mode: str
    settings: ProjectSettings
    report: ValidationReport
    inputs: Optional[pd.DataFrame] = None       # typed canonical input table (sorted)
    periods: Optional[pd.DataFrame] = None      # one row per reporting date
    wp_detail: Optional[pd.DataFrame] = None    # work-package mode only
    bac: Optional[float] = None
    value_sources: Dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.periods is not None and not self.report.has_blocking_errors


# -------------------------------------------------------------- file reading
def normalise_header(h) -> str:
    s = str(h).strip().lower().replace("%", " pct ")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def read_table(file_bytes: bytes, filename: str, sheet_name=0) -> pd.DataFrame:
    """Read CSV or XLSX as raw objects (no type coercion, so validation sees the real cell values)."""
    name = filename.lower()
    bio = io.BytesIO(file_bytes)
    if name.endswith(".csv"):
        try:
            df = pd.read_csv(bio, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except UnicodeDecodeError:
            bio.seek(0)
            df = pd.read_csv(bio, dtype=str, keep_default_na=False, encoding="latin-1")
    elif name.endswith(".xlsx"):
        df = pd.read_excel(bio, sheet_name=sheet_name, dtype=object, engine="openpyxl")
    else:
        raise ValueError("Unsupported file type. Upload a .csv or .xlsx file.")
    df = df.dropna(axis=1, how="all")
    # drop completely blank rows (e.g. trailing empty Excel rows) - these carry no data;
    # rows with ANY content are kept and validated.
    blank = df.apply(lambda r: all(is_missing(v) for v in r), axis=1)
    df = df.loc[~blank]
    df.attrs["blank_rows_skipped"] = int(blank.sum())
    df.columns = [str(c).strip() for c in df.columns]
    return df


def excel_sheet_names(file_bytes: bytes) -> List[str]:
    return pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl").sheet_names


def mode_fields(mode: str) -> List[str]:
    spec = MODE_FIELDS[mode]
    extra = ["ac_cumulative", "ac_period"] if spec["ac_choice"] else []
    return spec["required"] + extra + spec["optional"]


def suggest_mapping(columns: List[str], mode: str) -> Dict[str, Optional[str]]:
    """Map canonical field -> source column using exact names, then synonyms. Unknown columns stay unmapped."""
    norm = {normalise_header(c): c for c in columns}
    mapping: Dict[str, Optional[str]] = {}
    used = set()
    for f in mode_fields(mode):
        cands = [f] + SYNONYMS.get(f, [])
        if f == "activity_budget" and mode == "work_package":
            cands.append("budget")
        if f == "bac" and mode != "work_package":
            cands.append("budget")
        hit = next((norm[c] for c in cands if c in norm and norm[c] not in used), None)
        mapping[f] = hit
        if hit:
            used.add(hit)
    return mapping


# --------------------------------------------------------------- templates
def template(mode: str) -> pd.DataFrame:
    if mode == "progress":
        return pd.DataFrame({
            "reporting_date": ["2026-01-31", "2026-02-28"],
            "planned_progress_pct": [36.5, 52.0],
            "actual_progress_pct": [32.0, 44.0],
            "ac_cumulative": [13700000, 19200000],
            "bac": [40000000, 40000000],
            "independent_etc": ["", ""],
            "notes": ["Example row - replace with your data", ""],
        })
    if mode == "precalc":
        return pd.DataFrame({
            "reporting_date": ["2026-01-31", "2026-02-28"],
            "bac": [40000000, 40000000],
            "pv_cumulative": [14600000, 20800000],
            "ev_cumulative": [12800000, 17600000],
            "ac_cumulative": [13700000, 19200000],
            "independent_etc": ["", ""],
            "notes": ["Example row - replace with your data", ""],
        })
    if mode == "work_package":
        return pd.DataFrame({
            "reporting_date": ["2026-01-31", "2026-01-31", "2026-02-28", "2026-02-28"],
            "activity_id": ["WP1", "WP2", "WP1", "WP2"],
            "activity_name": ["Substructure", "Superstructure", "Substructure", "Superstructure"],
            "activity_budget": [8000000, 16000000, 8000000, 16000000],
            "planned_progress_pct": [100, 40, 100, 70],
            "actual_progress_pct": [100, 30, 100, 55],
            "ac_cumulative": [8400000, 5200000, 8400000, 9800000],
            "notes": ["Example rows - every WP must appear at every reporting date", "", "", ""],
        })
    raise ValueError(mode)


# ------------------------------------------------------------- main pipeline
def prepare(raw: pd.DataFrame, mapping: Dict[str, Optional[str]], settings: ProjectSettings,
            mode: str, first_data_row: int = 2) -> ProcessedData:
    """
    Validate and process one dataset. Never raises for bad data: problems are
    returned in ProcessedData.report. `first_data_row` is the spreadsheet row
    number of the first data row (2 for a file with one header row; 1 for a
    manual-entry table).
    """
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode}")
    rep = ValidationReport(records_read=len(raw))
    st = replace(settings)
    out = ProcessedData(mode=mode, settings=st, report=rep)

    if raw is None or len(raw) == 0:
        rep.error("The dataset contains no data rows.", fix="Add at least one reporting period.")
        return out
    skipped = raw.attrs.get("blank_rows_skipped", 0) if hasattr(raw, "attrs") else 0
    if skipped:
        rep.info(f"{skipped} completely blank row(s) were skipped (they contained no values).")

    spec = MODE_FIELDS[mode]
    mapping = {k: v for k, v in mapping.items() if v}
    # --- mapping checks
    for f in spec["required"]:
        if f not in mapping:
            rep.error(f"Required column '{FIELDS[f][0]}' is not mapped/present.", field=f,
                      fix=f"Add a '{f}' column (see the template) or map an existing column to it.")
    if spec["ac_choice"] and "ac_cumulative" not in mapping and "ac_period" not in mapping:
        rep.error("Actual cost is missing: supply cumulative AC or period AC.", field="ac_cumulative",
                  fix="Add an 'ac_cumulative' column (preferred) or an 'ac_period' column.")
    src_cols = list(mapping.values())
    dup = {c for c in src_cols if src_cols.count(c) > 1}
    for c in dup:
        rep.error(f"Source column '{c}' is mapped to more than one field.", fix="Map each column once.")
    missing_src = [c for c in src_cols if c not in raw.columns]
    for c in missing_src:
        rep.error(f"Mapped column '{c}' does not exist in the data.")
    allowed = set(mode_fields(mode))
    foreign = [f for f in mapping if f not in allowed]
    for f in foreign:
        rep.info(f"Field '{f}' is not used in {MODES[mode]} mode and was ignored.")
    unmapped = [c for c in raw.columns if c not in src_cols and not str(c).startswith("Unnamed")]
    if unmapped:
        looks = [c for c in unmapped if normalise_header(c) in
                 (["pv", "ev", "planned_value", "earned_value", "bcws", "bcwp", "pv_cumulative", "ev_cumulative"])]
        if looks and mode != "precalc":
            rep.warning(f"Column(s) {looks} look like supplied PV/EV but are NOT used in {MODES[mode]} mode; "
                        "PV and EV are derived from progress and budget instead.", field="pv_cumulative",
                        fix="Switch to 'Pre-calculated EVM Data' mode to use supplied PV/EV values.")
        rep.info(f"Column(s) not used by the tool (not interpreted): {unmapped}.")
    # --- wrong mode: an activity-level file uploaded as project-level data.
    # Without this check every activity row is read as a separate reporting period,
    # producing many misleading "duplicate date" and "decreasing value" messages.
    if mode != "work_package":
        wp_map = suggest_mapping([c for c in raw.columns], "work_package")
        if wp_map.get("activity_id") and wp_map.get("activity_budget"):
            rep.issues.clear()
            rep.error(f"This file has one row per activity (columns '{wp_map['activity_id']}' and "
                      f"'{wp_map['activity_budget']}'), but '{MODES[mode]}' expects one row per reporting date.",
                      field="data type",
                      fix="In step 1 ('What kind of data do you have?') choose 'Work-Package-Level Data', "
                          "then upload the same file again.")
            return out
    if rep.has_blocking_errors:
        return out

    # --- build typed canonical table
    df = pd.DataFrame({"source_row": [first_data_row + i for i in range(len(raw))]})
    for f, col in mapping.items():
        if f not in allowed:
            continue
        df[f] = list(raw[col].values)
    for f in list(df.columns):
        if f == "source_row":
            continue
        kind = FIELDS[f][2]
        vals = []
        for v, rown in zip(df[f], df["source_row"]):
            if kind == "date":
                x, err = to_date(v, st.dayfirst)
            elif kind in ("money", "pct"):
                x, err = to_number(v, allow_percent_sign=(kind == "pct"))
            else:
                x, err = (None if is_missing(v) else str(v).strip()), None
            if err:
                rep.error(f"{FIELDS[f][0]}: {err}.", rown, f, "Enter a plain number (or a YYYY-MM-DD date).")
            vals.append(x)
        if kind in ("money", "pct"):
            df[f] = pd.Series([float("nan") if x is None else x for x in vals], dtype="float64")
        elif kind == "date":
            df[f] = pd.Series([pd.NaT if x is None else x for x in vals], dtype="datetime64[ns]")
        else:
            df[f] = vals

    # --- optional columns that are completely empty carry no data: treat as not supplied
    for f in [c for c in df.columns if c != "source_row" and c not in spec["required"]]:
        if all(is_missing(v) for v in df[f]):
            df = df.drop(columns=[f])
            rep.info(f"Optional column '{FIELDS[f][0]}' is empty and was treated as not supplied.")
    if spec["ac_choice"] and "ac_cumulative" not in df.columns and "ac_period" not in df.columns:
        rep.error("Actual cost is missing: no cumulative AC or period AC values were supplied.",
                  field="ac_cumulative", fix="Enter cumulative AC (preferred) or period AC for every row.")

    # --- required values present
    req = list(spec["required"])
    for f in req:
        if f not in df.columns:
            continue
        for _, r in df.iterrows():
            if is_missing(r[f]):
                if not any(i.row == r["source_row"] and i.field == f for i in rep.errors):
                    rep.error(f"{FIELDS[f][0]} is missing.", r["source_row"], f,
                              "Fill in the value; missing values are never treated as zero.")

    # --- project-level constants from file
    for f in ("project_name", "currency"):
        if f in df.columns:
            u = sorted({v for v in df[f] if v})
            if len(u) > 1:
                rep.warning(f"Column '{f}' has different values {u}; '{u[0]}' is used.", field=f)
            if not u:
                continue
            if f == "project_name":
                if not (st.name or "").strip():
                    st.name = u[0]
                elif st.name.strip() != u[0]:
                    rep.info(f"Project name in settings ('{st.name}') is used instead of the file value ('{u[0]}').")
            else:
                st.currency = u[0]
    if "bac" in df.columns:
        u = sorted(set(df["bac"].dropna().round(6)))
        if len(u) > 1:
            rep.error(f"BAC changes between rows ({', '.join(f'{x:,.2f}' for x in u)}). Re-baselining within "
                      "one dataset is not supported.", field="bac",
                      fix="Use one approved BAC for all rows, or analyse each baseline separately.")
        elif len(u) == 1:
            if st.bac is not None and abs(st.bac - u[0]) > MONEY_TOL and mode != "work_package":
                rep.error(f"BAC in the file ({u[0]:,.2f}) differs from BAC in project settings ({st.bac:,.2f}).",
                          field="bac", fix="Make them equal (or clear the settings BAC to use the file value).")
            st.bac = u[0]
        if df["bac"].isna().any() and len(u) == 1:
            rep.info("Some rows have a blank BAC; the single BAC value in the file is used for the project.")

    # --- project settings
    if not (st.name or "").strip():
        rep.error("Project name is missing.", field="project_name", fix="Enter a project name in the project settings.")
    if st.baseline_start and st.baseline_finish and pd.Timestamp(st.baseline_start) >= pd.Timestamp(st.baseline_finish):
        rep.error("Baseline start date must be before the baseline completion date.", field="baseline")
    if mode != "work_package":
        if st.bac is None:
            rep.error("BAC is missing.", field="bac", fix="Enter BAC in project settings or add a 'bac' column.")
        elif st.bac <= 0:
            rep.error(f"BAC must be greater than zero (got {st.bac:,.2f}).", field="bac")

    # --- range / sign checks
    for f, label in (("planned_progress_pct", "Planned progress"), ("actual_progress_pct", "Actual progress")):
        if f in df.columns and (mode != "precalc"):
            check_percent_range(df, f, label, rep)
    for f in ("ac_cumulative", "pv_cumulative", "ev_cumulative", "activity_budget"):
        if f in df.columns:
            for _, r in df[df[f] < 0].iterrows():
                rep.error(f"{FIELDS[f][0]} is negative ({r[f]:,.2f}). Cumulative values cannot be negative.",
                          r["source_row"], f, "Correct the value; negative cumulative amounts need investigation.")
    if "ac_period" in df.columns:
        for _, r in df[df["ac_period"] < 0].iterrows():
            rep.warning(f"Period AC is negative ({r['ac_period']:,.2f}).", r["source_row"], "ac_period",
                        "Valid only for a genuine credit/reversal; confirm and explain in notes.")
    if "independent_etc" in df.columns:
        for _, r in df[df["independent_etc"] < 0].iterrows():
            rep.error("Independent ETC is negative.", r["source_row"], "independent_etc",
                      "Remaining cost cannot be negative.")

    # --- order
    if df["reporting_date"].notna().all():
        sorted_df = df.sort_values(["reporting_date"] + (["activity_id"] if mode == "work_package" else []),
                                   kind="stable").reset_index(drop=True)
        if mode != "work_package" and list(sorted_df["source_row"]) != list(df["source_row"]):
            rep.info("Rows were not in date order; they have been sorted chronologically for calculation "
                     "(the source file is unchanged).")
        df = sorted_df

    if mode == "work_package":
        _process_work_packages(df, st, rep, out)
    else:
        _process_project_level(df, st, rep, out, mode)

    if out.periods is not None:
        check_reporting_gaps(out.periods["reporting_date"], st.reporting_frequency, rep)
        check_dates_in_baseline(out.periods, st.baseline_start, st.baseline_finish, rep)
    out.inputs = df
    if rep.has_blocking_errors:
        out.periods = None
        out.wp_detail = None
    return out


def _dup_dates(df, rep, keys, label):
    d = df[df.duplicated(keys, keep=False) & df["reporting_date"].notna()]
    for _, r in d.iterrows():
        rep.error(f"Duplicate {label} for {r['reporting_date'].date()}"
                  + (f" / {r['activity_id']}" if "activity_id" in keys else "") + ".",
                  r["source_row"], "reporting_date", "Keep exactly one record per reporting date"
                  + (" and work package." if "activity_id" in keys else "."))


def _ac_series(df: pd.DataFrame, rep: ValidationReport):
    """Return (cumulative AC series, source label). Cumulative AC wins over period AC; never both added."""
    has_cum = "ac_cumulative" in df.columns
    has_per = "ac_period" in df.columns
    if has_cum:
        flagged = {i.row for i in rep.errors if i.field == "ac_cumulative"}
        for _, r in df[df["ac_cumulative"].isna() & ~df["source_row"].isin(flagged)].iterrows():
            rep.error("Cumulative AC is missing.", r["source_row"], "ac_cumulative",
                      "Fill in the value; missing cost is never treated as zero.")
        if has_per:
            rep.info("Both cumulative and period AC were supplied: cumulative AC is used as the source value; "
                     "period AC is only used to check consistency.")
            prev = None
            for _, r in df.iterrows():
                c, p = r["ac_cumulative"], r["ac_period"]
                if pd.notna(c) and pd.notna(p):
                    if prev is None and p - c > MONEY_TOL:
                        rep.warning(f"Period AC ({p:,.2f}) exceeds cumulative AC ({c:,.2f}) in the first period.",
                                    r["source_row"], "ac_period", "Check which column holds cumulative values.")
                    if prev is not None and abs((c - prev) - p) > MONEY_TOL:
                        rep.warning(f"Inconsistent cost data: cumulative AC rose by {c - prev:,.2f} but period AC "
                                    f"is {p:,.2f}. Cumulative AC has been used.", r["source_row"], "ac_period",
                                    "Correct whichever column is wrong.")
                prev = c if pd.notna(c) else prev
        return df["ac_cumulative"], "supplied"
    for _, r in df[df["ac_period"].isna()].iterrows():
        rep.error("Period AC is missing; cumulative AC cannot be derived.", r["source_row"], "ac_period",
                  "Enter the period cost (0 if genuinely nothing was spent).")
    rep.info("Cumulative AC was DERIVED as the running total of period AC, assuming the first row is the first "
             "reporting period since project start and that no period is missing.")
    return df["ac_period"].cumsum(), "derived: running total of period AC"


def _process_project_level(df, st, rep, out, mode):
    _dup_dates(df, rep, ["reporting_date"], "reporting date")
    bac = st.bac
    if rep.has_blocking_errors and (bac is None or bac <= 0):
        return
    if "ac_cumulative" not in df.columns and "ac_period" not in df.columns:
        return
    needed = ["planned_progress_pct", "actual_progress_pct"] if mode == "progress" else ["pv_cumulative", "ev_cumulative"]
    if any(c not in df.columns for c in needed):
        return
    periods = pd.DataFrame({"reporting_date": df["reporting_date"], "source_row": df["source_row"]})
    ac, ac_src = _ac_series(df, rep)
    periods["ac"] = ac.values
    if "ac_period" in df.columns:
        periods["ac_period"] = df["ac_period"].values
    if mode == "progress":
        periods["planned_pct"] = df["planned_progress_pct"].values
        periods["actual_pct"] = df["actual_progress_pct"].values
        if bac and bac > 0:
            periods["pv"] = periods["planned_pct"] / 100.0 * bac
            periods["ev"] = periods["actual_pct"] / 100.0 * bac
        out.value_sources = {"pv": "derived: planned % × BAC", "ev": "derived: actual physical % × BAC",
                             "ac": ac_src}
        rep.info("PV and EV were derived from cumulative progress × BAC. Actual progress must measure the share "
                 "of BUDGETED SCOPE physically completed, not elapsed time or a subjective impression.")
    else:
        periods["pv"] = df["pv_cumulative"].values
        periods["ev"] = df["ev_cumulative"].values
        if bac and bac > 0:
            periods["planned_pct"] = periods["pv"] / bac * 100.0
            periods["actual_pct"] = periods["ev"] / bac * 100.0
            for col, lab in (("pv", "PV"), ("ev", "EV")):
                for i, r in periods[periods[col] > bac + MONEY_TOL].iterrows():
                    rep.error(f"{lab} ({r[col]:,.2f}) exceeds BAC ({bac:,.2f}).", r["source_row"],
                              f"{col}_cumulative", f"{lab} can never exceed the total budget; check units/BAC.")
        out.value_sources = {"pv": "supplied", "ev": "supplied", "ac": ac_src,
                             "planned_pct": "derived: PV ÷ BAC", "actual_pct": "derived: EV ÷ BAC"}
    periods["independent_etc"] = df["independent_etc"].values if "independent_etc" in df.columns else float("nan")
    periods["notes"] = df["notes"].values if "notes" in df.columns else None
    # monotonic checks
    srt = periods.sort_values("reporting_date")
    user_field = {"planned_pct": "planned_progress_pct", "actual_pct": "actual_progress_pct",
                  "pv": "pv_cumulative", "ev": "ev_cumulative",
                  "ac": "ac_cumulative" if "ac_cumulative" in df.columns else "ac_period"}
    for col, lab in (("planned_pct", "planned progress"), ("actual_pct", "actual progress"),
                     ("pv", "PV"), ("ev", "EV"), ("ac", "AC")):
        if col in srt.columns and not (mode == "precalc" and col.endswith("pct")):
            if mode == "progress" and col in ("pv", "ev"):
                continue  # same information as the % checks
            check_non_decreasing(srt, col, lab, rep, field=user_field[col])
    out.periods = periods.reset_index(drop=True)
    out.bac = bac


def _process_work_packages(df, st, rep, out):
    _dup_dates(df, rep, ["reporting_date", "activity_id"], "record")
    if df["activity_id"].isna().any() or df["reporting_date"].isna().any() or rep.has_blocking_errors:
        return
    # budget must be constant per activity
    budgets = {}
    for aid, g in df.groupby("activity_id", sort=False):
        u = sorted(set(g["activity_budget"].dropna()))
        if len(u) > 1:
            rep.error(f"Budget for work package '{aid}' changes between dates ({u}).", int(g["source_row"].iloc[0]),
                      "activity_budget", "Use the approved budget consistently (re-baselining is not supported).")
        elif len(u) == 1:
            budgets[aid] = u[0]
            if u[0] == 0:
                rep.warning(f"Work package '{aid}' has a zero budget; it contributes cost but no PV/EV.",
                            int(g["source_row"].iloc[0]), "activity_budget",
                            "Acceptable for unbudgeted/unallocated costs; otherwise enter the budget.")
        if "activity_name" in g.columns and g["activity_name"].nunique(dropna=True) > 1:
            rep.warning(f"Work package '{aid}' has different names on different dates.",
                        int(g["source_row"].iloc[0]), "activity_name")
    # coverage: every WP at every date
    dates = sorted(df["reporting_date"].unique())
    all_wps = set(df["activity_id"])
    for d in dates:
        present = set(df.loc[df["reporting_date"] == d, "activity_id"])
        missing = sorted(all_wps - present)
        if missing:
            rep.error(f"Work package(s) {missing} have no record for {pd.Timestamp(d).date()}.",
                      field="activity_id",
                      fix="Report every work package at every date (repeat unchanged cumulative values). "
                          "Omitting one would silently drop its value from PV/EV/AC.")
    if rep.has_blocking_errors:
        return
    bac = float(sum(budgets.values()))
    if bac <= 0:
        rep.error("Total of work-package budgets is zero; BAC must be greater than zero.", field="activity_budget")
        return
    if st.bac is not None and abs(st.bac - bac) > MONEY_TOL:
        rep.warning(f"Work-package budgets total {bac:,.2f} but the project BAC in settings is {st.bac:,.2f}. "
                    "The data may not cover the whole project. Calculations use the total of the work-package "
                    "budgets as BAC for the scope analysed.", field="activity_budget",
                    fix="Add the missing work packages or correct the project BAC.")
    st.bac = bac
    # per-activity monotonic checks
    for aid, g in df.groupby("activity_id", sort=False):
        g = g.sort_values("reporting_date")
        for col, lab in (("planned_progress_pct", "planned progress"), ("actual_progress_pct", "actual progress"),
                         ("ac_cumulative", "AC")):
            check_non_decreasing(g, col, lab, rep, f" of '{aid}'")
    det = df.copy()
    det["pv_i"] = det["activity_budget"] * det["planned_progress_pct"] / 100.0
    det["ev_i"] = det["activity_budget"] * det["actual_progress_pct"] / 100.0
    det["ac_i"] = det["ac_cumulative"]
    det["cv_i"] = det["ev_i"] - det["ac_i"]
    det["sv_i"] = det["ev_i"] - det["pv_i"]
    agg = det.groupby("reporting_date", sort=True).agg(pv=("pv_i", "sum"), ev=("ev_i", "sum"), ac=("ac_i", "sum"),
                                                       source_row=("source_row", "min")).reset_index()
    agg["planned_pct"] = agg["pv"] / bac * 100.0
    agg["actual_pct"] = agg["ev"] / bac * 100.0
    agg["independent_etc"] = float("nan")
    agg["notes"] = None
    out.periods = agg
    out.wp_detail = det
    out.bac = bac
    out.value_sources = {"pv": "derived: Σ(budget × planned %)", "ev": "derived: Σ(budget × actual %)",
                         "ac": "derived: Σ work-package cumulative AC", "planned_pct": "derived: PV ÷ BAC",
                         "actual_pct": "derived: EV ÷ BAC (budget-weighted)"}
    rep.info(f"BAC = total of {len(budgets)} work-package budgets = {bac:,.2f}. Project progress is "
             "budget-weighted, not an unweighted average of work-package percentages.")
