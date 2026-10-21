"""
Forecasting: EAC, ETC, VAC, forecast overrun and TCPI.

Supported Estimate-at-Completion methods (user-selectable; none is "the" answer):

  A_CPI          EAC = BAC / CPI
                 Assumes the cost efficiency achieved so far continues for all
                 remaining work.
  B_CPI_SPI      EAC = AC + (BAC - EV) / (CPI x SPI)
                 Assumes remaining work is affected by both cost and schedule
                 performance (e.g. a schedule-driven acceleration cost). Usually
                 the most pessimistic when both indices are below 1.
  C_BUDGET_RATE  EAC = AC + (BAC - EV)
                 Assumes the variance so far is a one-off and remaining work will
                 be done exactly at its budgeted rate (CPI = 1 from now on).
  D_INDEPENDENT  EAC = AC + ETC(independent)
                 A bottom-up re-estimate of remaining cost supplied by the user.

  ETC        = EAC - AC
  VAC        = BAC - EAC        (negative = forecast to finish over budget)
  Overrun    = EAC - BAC        (forecast, NOT an overrun already incurred)
  Overrun %  = (EAC - BAC) / BAC x 100
  TCPI_BAC   = (BAC - EV) / (BAC - AC)   efficiency needed to finish within BAC
  TCPI_EAC   = (BAC - EV) / (EAC - AC)   efficiency needed to finish at that EAC
"""
from __future__ import annotations

from typing import Dict, Optional

from .metric import Metric, is_number, is_zero

METHODS: Dict[str, Dict[str, str]] = {
    "A_CPI": {
        "label": "A — Current cost efficiency continues (BAC / CPI)",
        "short": "BAC/CPI",
        "formula": "EAC = BAC / CPI",
        "assumption": ("The cost efficiency achieved to date (CPI) will continue for all remaining work. "
                       "Appropriate when past cost performance is considered representative of the future."),
    },
    "B_CPI_SPI": {
        "label": "B — Cost and schedule efficiency both affect remaining work",
        "short": "AC+(BAC−EV)/(CPI×SPI)",
        "formula": "EAC = AC + (BAC − EV) / (CPI × SPI)",
        "assumption": ("Remaining work will be performed at an efficiency equal to CPI × SPI — e.g. where "
                       "recovering the schedule is expected to cost extra. With both indices below 1 this is "
                       "normally the most pessimistic formula forecast."),
    },
    "C_BUDGET_RATE": {
        "label": "C — Remaining work at original budgeted rate",
        "short": "AC+(BAC−EV)",
        "formula": "EAC = AC + (BAC − EV)",
        "assumption": ("The variance to date is treated as a one-off; all remaining work will be completed at "
                       "exactly its budgeted cost (future CPI = 1). Optimistic unless the cause of the past "
                       "variance has been removed."),
    },
    "D_INDEPENDENT": {
        "label": "D — Independent (bottom-up) estimate of remaining cost",
        "short": "AC+ETC(user)",
        "formula": "EAC = AC + ETC supplied by user",
        "assumption": ("A fresh bottom-up estimate of the cost to finish the remaining work, prepared and "
                       "justified by the project team. Only as reliable as that estimate."),
    },
}

EARLY_STAGE_PCT = 10.0     # below this % complete, index-based forecasts are flagged for review
IMPLAUSIBLE_EAC_RATIO = 3.0  # EAC above this multiple of BAC is flagged for review

FORECAST_FIELDS = ("eac", "etc", "vac", "overrun", "overrun_pct", "tcpi_eac")


def _bad(*pairs) -> Optional[str]:
    names = [n for n, v in pairs if not is_number(v)]
    return f"Input not available: {', '.join(names)}." if names else None


def _flag_eac(eac: float, bac: float, ev: float, uses_indices: bool) -> Metric:
    notes = []
    if uses_indices and bac > 0 and ev / bac * 100 < EARLY_STAGE_PCT:
        notes.append(f"Only {ev / bac * 100:.1f}% of the work is complete; index-based forecasts are volatile "
                     f"this early (screening rule: < {EARLY_STAGE_PCT:.0f}%).")
    if bac > 0 and eac > IMPLAUSIBLE_EAC_RATIO * bac:
        notes.append(f"EAC exceeds {IMPLAUSIBLE_EAC_RATIO:.0f}× BAC; check the inputs before relying on it.")
    return Metric.review(eac, " ".join(notes)) if notes else Metric.ok(eac)


def eac_cpi(bac, ev, ac, cpi: Metric) -> Metric:
    msg = _bad(("BAC", bac), ("EV", ev), ("AC", ac))
    if msg:
        return Metric.undefined(msg)
    if not cpi.available:
        return Metric.undefined(f"Method A needs CPI, which is undefined: {cpi.note}")
    if cpi.value <= 0 or is_zero(cpi.value):
        return Metric.undefined("CPI is zero (no value earned yet), so BAC / CPI cannot be calculated.")
    return _flag_eac(float(bac) / cpi.value, float(bac), float(ev), True)


def eac_cpi_spi(bac, ev, ac, cpi: Metric, spi: Metric) -> Metric:
    msg = _bad(("BAC", bac), ("EV", ev), ("AC", ac))
    if msg:
        return Metric.undefined(msg)
    if not cpi.available:
        return Metric.undefined(f"Method B needs CPI, which is undefined: {cpi.note}")
    if not spi.available:
        return Metric.undefined(f"Method B needs SPI, which is undefined: {spi.note}")
    prod = cpi.value * spi.value
    if prod <= 0 or is_zero(prod):
        return Metric.undefined("CPI × SPI is zero (no value earned yet), so Method B cannot be calculated.")
    eac = float(ac) + (float(bac) - float(ev)) / prod
    return _flag_eac(eac, float(bac), float(ev), True)


def eac_budget_rate(bac, ev, ac) -> Metric:
    msg = _bad(("BAC", bac), ("EV", ev), ("AC", ac))
    if msg:
        return Metric.undefined(msg)
    return _flag_eac(float(ac) + (float(bac) - float(ev)), float(bac), float(ev), False)


def eac_independent(ac, independent_etc) -> Metric:
    if not is_number(independent_etc):
        return Metric.not_applicable("No independent ETC was supplied for this reporting date.")
    if not is_number(ac):
        return Metric.undefined("Input not available: AC.")
    if float(independent_etc) < 0:
        return Metric.undefined("The supplied independent ETC is negative, which is not a valid remaining cost.")
    return Metric.ok(float(ac) + float(independent_etc))


def etc_from_eac(eac: Metric, ac) -> Metric:
    if not eac.available:
        return Metric(None, eac.status if eac.status != "ok" else "undefined", f"EAC unavailable: {eac.note}")
    if not is_number(ac):
        return Metric.undefined("Input not available: AC.")
    etc = eac.value - float(ac)
    if etc < 0 and not is_zero(etc):
        return Metric.review(etc, "ETC is negative: the selected method or the inputs need review "
                                  "(a forecast cannot be below cost already incurred).")
    return Metric.ok(etc)


def _from_eac(eac: Metric, fn) -> Metric:
    if not eac.available:
        return Metric(None, eac.status, f"EAC unavailable: {eac.note}")
    return fn(eac.value)


def vac(bac, eac: Metric) -> Metric:
    if not is_number(bac):
        return Metric.undefined("Input not available: BAC.")
    return _from_eac(eac, lambda e: Metric.ok(float(bac) - e))


def forecast_overrun(bac, eac: Metric) -> Metric:
    if not is_number(bac):
        return Metric.undefined("Input not available: BAC.")
    return _from_eac(eac, lambda e: Metric.ok(e - float(bac)))


def forecast_overrun_pct(bac, eac: Metric) -> Metric:
    if not is_number(bac) or float(bac) <= 0:
        return Metric.undefined("BAC must be greater than zero to express the overrun as a percentage.")
    return _from_eac(eac, lambda e: Metric.ok((e - float(bac)) / float(bac) * 100.0))


def tcpi_to_bac(bac, ev, ac) -> Metric:
    msg = _bad(("BAC", bac), ("EV", ev), ("AC", ac))
    if msg:
        return Metric.undefined(msg)
    work_left = float(bac) - float(ev)
    funds_left = float(bac) - float(ac)
    if work_left <= 0 or is_zero(work_left):
        return Metric.not_applicable("No work remains (EV = BAC), so a to-complete index does not apply.")
    if funds_left <= 0 or is_zero(funds_left):
        return Metric.undefined("Actual cost has already reached or exceeded BAC while work remains: "
                                "finishing within the original budget is no longer possible.")
    return Metric.ok(work_left / funds_left)


def tcpi_to_eac(bac, ev, ac, eac: Metric) -> Metric:
    msg = _bad(("BAC", bac), ("EV", ev), ("AC", ac))
    if msg:
        return Metric.undefined(msg)
    work_left = float(bac) - float(ev)
    if work_left <= 0 or is_zero(work_left):
        return Metric.not_applicable("No work remains (EV = BAC), so a to-complete index does not apply.")
    if not eac.available:
        return Metric(None, eac.status, f"EAC unavailable: {eac.note}")
    funds_left = eac.value - float(ac)
    if funds_left <= 0 or is_zero(funds_left):
        return Metric.undefined("EAC − AC is zero or negative, so TCPI against this EAC is undefined.")
    return Metric.ok(work_left / funds_left)


def forecast(method: str, *, bac, ev, ac, cpi: Metric, spi: Metric, independent_etc=None) -> Dict[str, Metric]:
    if method == "A_CPI":
        eac = eac_cpi(bac, ev, ac, cpi)
    elif method == "B_CPI_SPI":
        eac = eac_cpi_spi(bac, ev, ac, cpi, spi)
    elif method == "C_BUDGET_RATE":
        eac = eac_budget_rate(bac, ev, ac)
    elif method == "D_INDEPENDENT":
        eac = eac_independent(ac, independent_etc)
    else:
        raise ValueError(f"Unknown forecasting method: {method}")
    return {
        "eac": eac,
        "etc": etc_from_eac(eac, ac),
        "vac": vac(bac, eac),
        "overrun": forecast_overrun(bac, eac),
        "overrun_pct": forecast_overrun_pct(bac, eac),
        "tcpi_eac": tcpi_to_eac(bac, ev, ac, eac),
    }
