"""
Core EVM metrics (status-date, cumulative values).

All inputs are CUMULATIVE to the reporting date and in the same currency unit.
Nothing here rounds; rounding happens only in src/formatting.py for display.

    CV  = EV - AC          (positive = favourable)
    SV  = EV - PV          (positive = favourable; a money measure, not days)
    CPI = EV / AC          (>1 favourable)
    SPI = EV / PV          (>1 favourable)
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from .metric import Metric, is_number, is_zero
from . import forecasting as fc


def _missing(*pairs) -> Optional[Metric]:
    names = [n for n, v in pairs if not is_number(v)]
    if names:
        return Metric.undefined(f"Input not available: {', '.join(names)}.")
    return None


def cost_variance(ev, ac) -> Metric:
    m = _missing(("EV", ev), ("AC", ac))
    return m or Metric.ok(float(ev) - float(ac))


def schedule_variance(ev, pv) -> Metric:
    m = _missing(("EV", ev), ("PV", pv))
    return m or Metric.ok(float(ev) - float(pv))


def cost_performance_index(ev, ac) -> Metric:
    m = _missing(("EV", ev), ("AC", ac))
    if m:
        return m
    ev, ac = float(ev), float(ac)
    if is_zero(ac):
        return Metric.undefined("AC is zero (no cost recorded yet), so CPI = EV/AC cannot be calculated.")
    if ac < 0:
        return Metric.undefined("AC is negative, which is not a valid cumulative cost; CPI not calculated.")
    return Metric.ok(ev / ac)


def schedule_performance_index(ev, pv) -> Metric:
    m = _missing(("EV", ev), ("PV", pv))
    if m:
        return m
    ev, pv = float(ev), float(pv)
    if is_zero(pv):
        return Metric.undefined("PV is zero (no work was scheduled by this date), so SPI = EV/PV cannot be calculated.")
    if pv < 0:
        return Metric.undefined("PV is negative, which is not valid; SPI not calculated.")
    return Metric.ok(ev / pv)


def percent_of_bac(x, bac, label: str) -> Metric:
    m = _missing((label, x), ("BAC", bac))
    if m:
        return m
    if float(bac) <= 0:
        return Metric.undefined("BAC must be greater than zero.")
    return Metric.ok(float(x) / float(bac) * 100.0)


def compute_period_metrics(bac, pv, ev, ac, independent_etc=None) -> Dict[str, Metric]:
    """Every metric for one reporting date. Keys are stable column names."""
    out: Dict[str, Metric] = {
        "bac": Metric.ok(bac) if is_number(bac) else Metric.undefined("BAC not available."),
        "pv": Metric.ok(pv) if is_number(pv) else Metric.undefined("PV not available."),
        "ev": Metric.ok(ev) if is_number(ev) else Metric.undefined("EV not available."),
        "ac": Metric.ok(ac) if is_number(ac) else Metric.undefined("AC not available."),
    }
    out["cv"] = cost_variance(ev, ac)
    out["sv"] = schedule_variance(ev, pv)
    out["cpi"] = cost_performance_index(ev, ac)
    out["spi"] = schedule_performance_index(ev, pv)
    out["pct_planned"] = percent_of_bac(pv, bac, "PV")
    out["pct_complete"] = percent_of_bac(ev, bac, "EV")
    out["pct_spent"] = percent_of_bac(ac, bac, "AC")
    out["tcpi_bac"] = fc.tcpi_to_bac(bac, ev, ac)
    for key in fc.METHODS:
        f = fc.forecast(key, bac=bac, ev=ev, ac=ac, cpi=out["cpi"], spi=out["spi"],
                        independent_etc=independent_etc)
        for name, metric in f.items():
            out[f"{name}_{key}"] = metric
    return out


def compute_results(periods: pd.DataFrame, bac: float) -> pd.DataFrame:
    """
    Apply compute_period_metrics to every reporting date.

    `periods` must contain columns reporting_date, pv, ev, ac and optionally
    independent_etc (cumulative values, already validated and sorted).
    Returns one row per date with, for every metric X, columns
    X (float or NaN), X__status and X__note.  NaN is only a storage
    placeholder: the status column says *why* there is no number.
    """
    rows = []
    for _, r in periods.iterrows():
        etc_ind = r.get("independent_etc") if "independent_etc" in periods.columns else None
        mets = compute_period_metrics(bac, r.get("pv"), r.get("ev"), r.get("ac"), etc_ind)
        row = {"reporting_date": r["reporting_date"]}
        for k, m in mets.items():
            row[k] = m.value if m.value is not None else float("nan")
            row[f"{k}__status"] = m.status
            row[f"{k}__note"] = m.note
        rows.append(row)
    return pd.DataFrame(rows)


def metric_from_row(row, name: str) -> Metric:
    """Rebuild a Metric from a compute_results row (so the UI never reads raw NaN)."""
    status = row.get(f"{name}__status")
    note = row.get(f"{name}__note", "")
    if status is None:
        return Metric.undefined(f"Metric '{name}' was not calculated.")
    value = row.get(name)
    value = float(value) if is_number(value) else None
    return Metric(value, status, note if isinstance(note, str) else "")
