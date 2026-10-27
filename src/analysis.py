"""
Work-package analysis at one reporting date (work-package input mode only).

  * work_package_status  - PV, EV, AC, CV, SV, CPI, SPI and a health status for each work package,
                           using the same screening thresholds as the project-level health check.
  * problem_activities   - the work packages / activities with the largest shortfall, ranked by the
                           more negative of CV and SV (both are in money, so they are comparable).

Pure functions of ProcessedData.wp_detail; no Streamlit here.
"""
from __future__ import annotations

import pandas as pd

from .commentary import CRITICAL, FAVOURABLE, INSUFFICIENT, WARNING, HealthThresholds

NOT_STARTED = "Not started"
MONEY_TOL = 0.005          # variances smaller than half a paisa/cent are treated as zero


def _ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return (num / den).where(den > 0)


def _status(cpi: float, spi: float, pv: float, ev: float, ac: float, th: HealthThresholds) -> str:
    if pv <= MONEY_TOL and ev <= MONEY_TOL and ac <= MONEY_TOL:
        return NOT_STARTED
    if pd.isna(cpi) or pd.isna(spi):
        return INSUFFICIENT
    worst = min(cpi, spi)
    if worst < th.index_critical_below:
        return CRITICAL
    if worst < th.index_warning_below:
        return WARNING
    return FAVOURABLE


def work_package_status(wp_detail: pd.DataFrame, date, th: HealthThresholds) -> pd.DataFrame:
    d = wp_detail[wp_detail["reporting_date"] == pd.Timestamp(date)].copy()
    name = d["activity_name"] if "activity_name" in d else pd.Series("", index=d.index)
    out = pd.DataFrame({
        "activity_id": d["activity_id"].astype(str), "activity_name": name.fillna("").astype(str),
        "budget": d["activity_budget"], "pv": d["pv_i"], "ev": d["ev_i"], "ac": d["ac_i"],
        "cv": d["cv_i"], "sv": d["sv_i"],
    })
    out["cpi"] = _ratio(out["ev"], out["ac"])
    out["spi"] = _ratio(out["ev"], out["pv"])
    out["status"] = [_status(c, s, p, e, a, th) for c, s, p, e, a in
                     zip(out["cpi"], out["spi"], out["pv"], out["ev"], out["ac"])]
    return out.reset_index(drop=True)


def problem_activities(wp_detail: pd.DataFrame, date, n: int = 5) -> pd.DataFrame:
    t = work_package_status(wp_detail, date, HealthThresholds())
    t["order"] = range(len(t))
    t["worst_variance"] = t[["cv", "sv"]].min(axis=1)
    t = t[t["worst_variance"] < -MONEY_TOL]
    t["main_issue"] = ["Behind schedule" if sv <= cv else "Over budget" for cv, sv in zip(t["cv"], t["sv"])]
    t = t.sort_values(["worst_variance", "order"]).head(n)
    return t.drop(columns=["order"]).reset_index(drop=True)
