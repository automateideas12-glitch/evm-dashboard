"""
Input validation shared by file upload and manual entry.

Three severities:
  ERROR    blocks loading — the data cannot be calculated reliably.
  WARNING  data loads, but something needs a human look (e.g. cumulative
           progress went down, a reporting period is missing).
  INFO     a note on how the data was interpreted (e.g. "AC derived from
           period costs").

Unfavourable *results* (negative CV, CPI < 1) are never validation issues:
they are valid findings and are always displayed.

Nothing here modifies, repairs, fills or deletes user data.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

ERROR, WARNING, INFO = "error", "warning", "info"
MONEY_TOL = 0.5  # currency units; differences below this are treated as rounding


@dataclass
class Issue:
    severity: str
    message: str
    row: Optional[int] = None      # spreadsheet-style row number (header = row 1)
    field: Optional[str] = None
    fix: str = ""


@dataclass
class ValidationReport:
    issues: List[Issue] = field(default_factory=list)
    records_read: int = 0

    def add(self, severity, message, row=None, field=None, fix=""):
        self.issues.append(Issue(severity, message, row, field, fix))

    def error(self, *a, **k):
        self.add(ERROR, *a, **k)

    def warning(self, *a, **k):
        self.add(WARNING, *a, **k)

    def info(self, *a, **k):
        self.add(INFO, *a, **k)

    @property
    def errors(self):
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self):
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def infos(self):
        return [i for i in self.issues if i.severity == INFO]

    @property
    def has_blocking_errors(self) -> bool:
        return bool(self.errors)

    def rows_with_errors(self) -> set:
        return {i.row for i in self.errors if i.row is not None}

    def to_frame(self) -> pd.DataFrame:
        order = {ERROR: 0, WARNING: 1, INFO: 2}
        rows = [{"Severity": i.severity.upper(), "Row": i.row if i.row is not None else "",
                 "Field": i.field or "", "Problem": i.message, "How to resolve": i.fix}
                for i in sorted(self.issues, key=lambda x: (order[x.severity], x.row or 0))]
        return pd.DataFrame(rows, columns=["Severity", "Row", "Field", "Problem", "How to resolve"])


# ------------------------------------------------------------------ parsing
_MISSING_TOKENS = {"", "nan", "none", "null", "na", "n/a", "#n/a"}
_CURRENCY = re.compile(r"(₹|\$|€|£|\bINR\b|\bRs\.?)", re.IGNORECASE)
_ISO_DATE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}([ T].*)?$")


def is_missing(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if v is pd.NaT:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(v, str) and v.strip().lower() in _MISSING_TOKENS


def to_number(v, allow_percent_sign: bool = False):
    """
    Convert one cell to float. Returns (value, error_message).
    value is None when the cell is missing. Accepted normalisations (documented,
    value-preserving): thousands separators, spaces, currency symbols,
    accounting negatives "(1,000)", and a trailing % for percentage fields.
    """
    if is_missing(v):
        return None, None
    if isinstance(v, bool):
        return None, f"'{v}' is not a number"
    if isinstance(v, (int, float)):
        f = float(v)
        return (f, None) if math.isfinite(f) else (None, f"'{v}' is not a finite number")
    s = str(v).strip()
    raw = s
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = _CURRENCY.sub("", s).replace(",", "").replace(" ", "").replace(" ", "")
    if s.endswith("%"):
        if not allow_percent_sign:
            return None, f"'{raw}' contains a % sign but this field is a money amount"
        s = s[:-1]
    try:
        f = float(s)
    except ValueError:
        return None, f"'{raw}' is not a number"
    if not math.isfinite(f):
        return None, f"'{raw}' is not a finite number"
    return (-f if neg else f), None


def to_date(v, dayfirst: bool = True):
    """Returns (Timestamp normalised to midnight, error_message)."""
    if is_missing(v):
        return None, None
    if isinstance(v, (pd.Timestamp,)) or hasattr(v, "year") and hasattr(v, "month"):
        try:
            return pd.Timestamp(v).normalize(), None
        except (ValueError, TypeError):
            return None, f"'{v}' is not a valid date"
    s = str(v).strip()
    try:
        if _ISO_DATE.match(s):
            ts = pd.to_datetime(s, format="mixed", dayfirst=False)
        else:
            ts = pd.to_datetime(s, format="mixed", dayfirst=dayfirst)
    except (ValueError, TypeError, OverflowError):
        return None, f"'{s}' is not a recognised date (use YYYY-MM-DD)"
    if pd.isna(ts):
        return None, f"'{s}' is not a recognised date (use YYYY-MM-DD)"
    return ts.normalize(), None


# --------------------------------------------------------------- checks
def check_percent_range(df: pd.DataFrame, col: str, label: str, report: ValidationReport):
    for _, r in df.iterrows():
        v = r[col]
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        if v < 0 or v > 100:
            report.error(f"{label} is {v:g}%, outside the allowed 0–100% range.", r["source_row"], col,
                         "Enter cumulative progress as a percentage between 0 and 100.")
    vals = df[col].dropna()
    if len(vals) and vals.max() <= 1.0 and vals.max() > 0:
        report.warning(f"All {label} values are ≤ 1. If these are fractions (0.45 = 45%), multiply them by 100; "
                       "the tool reads them as percentages, so 0.45 means 0.45%.", None, col,
                       "Convert fractions to percentages in the source file.")


def check_non_decreasing(df: pd.DataFrame, col: str, label: str, report: ValidationReport,
                         group_label: str = "", field: str = None):
    """df must already be sorted by date. Flags decreases as warnings (never auto-corrected)."""
    prev = None
    prev_row = None
    for _, r in df.iterrows():
        v = r[col]
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        if prev is not None and v < prev - 1e-9:
            report.warning(
                f"Cumulative {label}{group_label} decreases from {prev:,.2f} (row {prev_row}) to {v:,.2f}. "
                "Cumulative values normally never fall.", r["source_row"], field or col,
                "Correct the value, or record the reason (re-measurement, credit note, re-baseline) in the notes "
                "column. The value has not been changed by the tool.")
        prev, prev_row = v, r["source_row"]


def check_reporting_gaps(dates: pd.Series, frequency: str, report: ValidationReport):
    d = sorted(pd.Series(dates).dropna().unique())
    if frequency not in ("Monthly", "Weekly") or len(d) < 2:
        return
    for a, b in zip(d[:-1], d[1:]):
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        if frequency == "Monthly":
            gap = (b.year - a.year) * 12 + (b.month - a.month)
            if gap > 1:
                report.warning(f"{gap - 1} monthly reporting period(s) appear to be missing between "
                               f"{a.date()} and {b.date()}.", None, "reporting_date",
                               "Add the missing period(s), or set the reporting frequency to 'Irregular'. "
                               "Charts will not draw a line across the gap as if it were observed.")
        elif (b - a).days > 8:
            report.warning(f"Gap of {(b - a).days} days between {a.date()} and {b.date()} with weekly reporting.",
                           None, "reporting_date", "Add the missing week(s) or change the reporting frequency.")


def check_dates_in_baseline(df: pd.DataFrame, start, finish, report: ValidationReport):
    for _, r in df.iterrows():
        d = r["reporting_date"]
        if d is None or pd.isna(d):
            continue
        if start is not None and d < pd.Timestamp(start):
            report.warning(f"Reporting date {d.date()} is before the baseline start {pd.Timestamp(start).date()}.",
                           r["source_row"], "reporting_date", "Check the date or the baseline start date.")
        if finish is not None and d > pd.Timestamp(finish):
            report.warning(f"Reporting date {d.date()} is after the baseline completion "
                           f"{pd.Timestamp(finish).date()}. PV has reached BAC, so SPI tends towards 1 as work "
                           "finishes even if the project is late.", r["source_row"], "reporting_date",
                           "Valid for a late project; interpret SPI with care.")
