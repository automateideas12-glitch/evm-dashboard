"""
Project-health screening and plain-language commentary — rule-based, offline.

Design rules
  * Observed facts, possible explanations and recommended investigations are
    kept in separate sections.
  * No cause is ever asserted (e.g. "labour productivity fell") — the data
    cannot show causes. The commentary only states what the numbers show and
    suggests where to look.
  * Thresholds are SCREENING RULES chosen by the team and configurable by the
    user. They are not industry standards.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from .evm_calculations import metric_from_row
from .forecasting import METHODS
from .formatting import format_index, format_money, format_pct
from .metric import Metric

FAVOURABLE, WARNING, CRITICAL, INSUFFICIENT = "Favourable", "Warning", "Critical", "Insufficient data"
_RANK = {FAVOURABLE: 0, WARNING: 1, CRITICAL: 2}


@dataclass
class HealthThresholds:
    index_warning_below: float = 1.00   # CPI/SPI below this -> Warning
    index_critical_below: float = 0.90  # CPI/SPI below this -> Critical
    overrun_warning_above_pct: float = 0.0    # forecast overrun % above this -> Warning
    overrun_critical_above_pct: float = 10.0  # forecast overrun % above this -> Critical
    tcpi_gap: float = 0.10  # TCPI_BAC more than this above CPI -> "BAC unlikely" flag


def _index_status(m: Metric, th: HealthThresholds) -> str:
    if not m.available:
        return INSUFFICIENT
    if m.value < th.index_critical_below:
        return CRITICAL
    if m.value < th.index_warning_below:
        return WARNING
    return FAVOURABLE


def _overrun_status(m: Metric, th: HealthThresholds) -> str:
    if not m.available:
        return INSUFFICIENT
    if m.value > th.overrun_critical_above_pct:
        return CRITICAL
    if m.value > th.overrun_warning_above_pct:
        return WARNING
    return FAVOURABLE


def classify(row, method: str, th: HealthThresholds) -> Dict:
    """
    Overall = Critical if any component is Critical; otherwise Insufficient data if any
    component is unavailable; otherwise the worst of Warning/Favourable.
    (Missing indices can never make a project look healthy.)
    """
    cpi, spi = metric_from_row(row, "cpi"), metric_from_row(row, "spi")
    ovr = metric_from_row(row, f"overrun_pct_{method}")
    comps = [
        {"Indicator": "Cost performance (CPI)", "Value": format_index(cpi.value),
         "Status": _index_status(cpi, th),
         "Rule": f"Warning < {th.index_warning_below:.2f}; Critical < {th.index_critical_below:.2f}",
         "Note": cpi.note},
        {"Indicator": "Schedule performance (SPI)", "Value": format_index(spi.value),
         "Status": _index_status(spi, th),
         "Rule": f"Warning < {th.index_warning_below:.2f}; Critical < {th.index_critical_below:.2f}",
         "Note": spi.note},
        {"Indicator": f"Forecast overrun (method {method[0]})", "Value": format_pct(ovr.value, 2),
         "Status": _overrun_status(ovr, th),
         "Rule": f"Warning > {th.overrun_warning_above_pct:.1f}%; Critical > {th.overrun_critical_above_pct:.1f}%",
         "Note": ovr.note},
    ]
    statuses = [c["Status"] for c in comps]
    if CRITICAL in statuses:
        overall = CRITICAL
    elif INSUFFICIENT in statuses:
        overall = INSUFFICIENT
    else:
        overall = max(statuses, key=lambda s: _RANK[s])
    return {"overall": overall, "components": comps}


def generate_commentary(results: pd.DataFrame, idx: int, method: str, th: HealthThresholds,
                        currency: str = "INR", unit: str = "lakh",
                        wp_detail: Optional[pd.DataFrame] = None,
                        notes: Optional[str] = None,
                        baseline_finish=None) -> Dict[str, List[str]]:
    row = results.iloc[idx]
    prev = results.iloc[idx - 1] if idx > 0 else None
    M = lambda name, r=row: metric_from_row(r, name)  # noqa: E731
    money = lambda v: format_money(v, currency, unit)  # noqa: E731
    date = pd.Timestamp(row["reporting_date"]).date()
    sec: Dict[str, List[str]] = {"Observed facts": [], "Change since previous report": [],
                                 "Forecast (assumption-based)": [], "Suggested investigations": [],
                                 "Data and interpretation caveats": []}
    f, inv, cav = sec["Observed facts"], sec["Suggested investigations"], sec["Data and interpretation caveats"]
    pv, ev, ac, bac = M("pv"), M("ev"), M("ac"), M("bac")
    cv, sv, cpi, spi = M("cv"), M("sv"), M("cpi"), M("spi")

    f.append(f"As of {date}, earned value is {money(ev.value)} ({format_pct(M('pct_complete').value)} of BAC) "
             f"against planned value of {money(pv.value)} ({format_pct(M('pct_planned').value)}); actual cost is "
             f"{money(ac.value)} ({format_pct(M('pct_spent').value)} of BAC {money(bac.value)}).")
    if cpi.available:
        word = "favourable" if cv.value > 0 else ("unfavourable" if cv.value < 0 else "neutral")
        f.append(f"Cost: CV = EV − AC = {money(cv.value)} ({word}). CPI = {format_index(cpi.value)}, i.e. "
                 f"{format_money(cpi.value, currency, 'units', 2)} of budgeted work earned per "
                 f"{format_money(1, currency, 'units')} spent.")
    else:
        f.append(f"Cost: CPI is undefined — {cpi.note}")
    if spi.available:
        word = "ahead of" if sv.value > 0 else ("behind" if sv.value < 0 else "on")
        f.append(f"Schedule: SV = EV − PV = {money(sv.value)}; SPI = {format_index(spi.value)}. In budget-value "
                 f"terms the project is {word} plan, earning value at {spi.value * 100:.0f}% of the planned rate. "
                 "SV is a money measure, not a number of days.")
    else:
        f.append(f"Schedule: SPI is undefined — {spi.note}")
    if ac.available and bac.available and ac.value > bac.value:
        f.append(f"Actual cost already EXCEEDS BAC by {money(ac.value - bac.value)} — an overrun already incurred, "
                 "not a forecast.")
    if notes:
        f.append(f"Note recorded by the user for this period (not verified by the tool): “{notes}”")

    # ---- change since previous
    ch = sec["Change since previous report"]
    if prev is None:
        ch.append("First reporting period — no earlier report to compare with.")
    else:
        deteriorated = []
        for key, label in (("cpi", "CPI"), ("spi", "SPI")):
            a, b = M(key, prev), M(key)
            if a.available and b.available:
                d = b.value - a.value
                trend = "improved" if d > 0.0005 else ("deteriorated" if d < -0.0005 else "was unchanged")
                ch.append(f"{label} {trend}: {format_index(a.value, 4)} → {format_index(b.value, 4)} ({d:+.4f}).")
                if d < -0.0005:
                    deteriorated.append(label)
        a_ev, a_ac = M("ev", prev), M("ac", prev)
        if all(m.available for m in (a_ev, a_ac, ev, ac)):
            dev, dac = ev.value - a_ev.value, ac.value - a_ac.value
            ch.append(f"This period: value earned {money(dev)}, cost incurred {money(dac)}.")
            if dac > 0 and abs(dev) < 1e-6:
                inv.append("Cost was recorded this period with no additional earned value. Confirm whether this "
                           "reflects advance payments, unrecorded progress, rework or mis-coded costs.")
        streak = 0
        for j in range(idx, 0, -1):
            c1, c0 = metric_from_row(results.iloc[j], "cpi"), metric_from_row(results.iloc[j - 1], "cpi")
            if c1.available and c0.available and c1.value < c0.value - 0.0005:
                streak += 1
            else:
                break
        if streak >= 3:
            ch.append(f"CPI has fallen for {streak} consecutive reports — a sustained trend rather than a one-off.")
        if deteriorated:
            ch.append(f"Deteriorated since last report: {', '.join(deteriorated)}.")

    # ---- forecast
    fc = sec["Forecast (assumption-based)"]
    eac, etc, vac, ovp = M(f"eac_{method}"), M(f"etc_{method}"), M(f"vac_{method}"), M(f"overrun_pct_{method}")
    fc.append(f"Selected method: {METHODS[method]['label']}. Assumption: {METHODS[method]['assumption']}")
    if eac.available:
        direction = "over" if vac.value < 0 else "within"
        fc.append(f"EAC = {money(eac.value)}; ETC = {money(etc.value)}; VAC = {money(vac.value)} — forecast to finish "
                  f"{direction} budget ({format_pct(ovp.value, 2)} vs BAC). This is a forecast under the stated "
                  "assumption, not a guaranteed final cost.")
        if eac.status == "review":
            fc.append(f"⚠ {eac.note}")
        if etc.status == "review":
            fc.append(f"⚠ {etc.note}")
    else:
        fc.append(f"EAC is not available with this method: {eac.note}")
    vals = [M(f"eac_{k}").value for k in ("A_CPI", "B_CPI_SPI", "C_BUDGET_RATE") if M(f"eac_{k}").available]
    if len(vals) >= 2:
        fc.append(f"Formula methods A–C give EAC between {money(min(vals))} and {money(max(vals))}; the spread "
                  "reflects different assumptions about future performance.")
    tb = M("tcpi_bac")
    if tb.available:
        line = (f"To finish within the original BAC, remaining work must be performed at TCPI = "
                f"{format_index(tb.value)}")
        if cpi.available:
            gap = tb.value - cpi.value
            line += f", compared with CPI achieved to date of {format_index(cpi.value)} (gap {gap:+.3f})."
            if gap > th.tcpi_gap:
                line += (f" Under the screening rule (gap > {th.tcpi_gap:.2f}), completing within BAC is considered "
                         "unlikely without a change in approach, scope or budget.")
        fc.append(line)
    else:
        fc.append(f"TCPI to BAC: {tb.note}")

    # ---- investigations (where to look, never asserted causes)
    if cpi.available and cpi.value < 1:
        inv.append("Compare EV with AC by work package / cost account to locate where the cost variance arises, "
                   "then establish the cause with the site and commercial teams.")
    if spi.available and spi.value < 1:
        inv.append("Check activities on the critical path against the programme. SPI is budget-weighted and does "
                   "not show by itself whether critical activities are late.")
    if eac.available and vac.value < 0:
        inv.append("Review the forecast with the estimating team; consider a bottom-up re-estimate (method D) of "
                   "the remaining work.")
    if wp_detail is not None and len(wp_detail):
        d = wp_detail[wp_detail["reporting_date"] == row["reporting_date"]]
        worst_cv = d.nsmallest(3, "cv_i")
        worst_cv = worst_cv[worst_cv["cv_i"] < 0]
        if len(worst_cv):
            items = "; ".join(f"{r.activity_id} {r.activity_name or ''} (CV {money(r.cv_i)})".replace("  ", " ")
                              for r in worst_cv.itertuples())
            f.append(f"Largest negative cost variances by work package: {items}.")
        worst_sv = d.nsmallest(3, "sv_i")
        worst_sv = worst_sv[worst_sv["sv_i"] < 0]
        if len(worst_sv):
            items = "; ".join(f"{r.activity_id} {r.activity_name or ''} (SV {money(r.sv_i)})".replace("  ", " ")
                              for r in worst_sv.itertuples())
            f.append(f"Largest negative schedule variances by work package: {items}.")
    inv.append("Confirm that physical progress for the major work packages was measured against budgeted scope "
               "(quantities installed), not estimated from time elapsed.")

    # ---- caveats
    pc = M("pct_complete")
    if pc.available and pc.value < 10:
        cav.append("Less than 10% of the work is complete; indices and index-based forecasts are volatile at this "
                   "stage.")
    pp = M("pct_planned")
    late = baseline_finish is not None and pd.Timestamp(row["reporting_date"]) > pd.Timestamp(baseline_finish)
    if (pp.available and pp.value >= 99.999) or late:
        cav.append("PV has reached BAC (planned finish passed). From here SPI rises towards 1.0 as work completes "
                   "even if the project is late; use the programme to judge delay.")
    if method == "D_INDEPENDENT" and not eac.available:
        cav.append("Method D needs an independent ETC for this reporting date.")
    cav.append("Health labels use configurable screening thresholds chosen by the team, not industry standards; "
               "they support, not replace, professional judgement.")
    return sec
