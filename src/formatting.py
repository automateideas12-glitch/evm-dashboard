"""
Display formatting ONLY. Calculations are never rounded; these functions are
applied at the last step, when a value is shown to the user or written to a
human-readable report.
"""
from __future__ import annotations

from typing import Optional

from .metric import Metric, NOT_APPLICABLE, REVIEW, UNDEFINED, is_number

SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
UNITS = {"units": (1.0, ""), "lakh": (1e5, " lakh"), "crore": (1e7, " cr"), "million": (1e6, " M")}


def indian_grouping(n: int) -> str:
    """1234567 -> '12,34,567' (Indian numbering)."""
    s = str(abs(int(n)))
    if len(s) <= 3:
        out = s
    else:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        out = ",".join(parts) + "," + tail
    return ("-" if n < 0 else "") + out


def format_money(value, currency: str = "INR", unit: str = "units", decimals: Optional[int] = None) -> str:
    if not is_number(value):
        return "Undefined"
    value = float(value)
    sym = SYMBOLS.get(currency, f"{currency} ")
    div, suffix = UNITS.get(unit, (1.0, ""))
    sign = "-" if value < 0 else ""
    v = abs(value) / div
    if unit == "units":
        d = 0 if decimals is None else decimals
        whole_txt, _, frac = f"{v:.{d}f}".partition(".")
        whole = int(whole_txt)
        body = (indian_grouping(whole) if currency == "INR" else f"{whole:,}") + (f".{frac}" if frac else "")
    else:
        d = 2 if decimals is None else decimals
        body = f"{v:,.{d}f}"
    return f"{sign}{sym}{body}{suffix}"


def format_index(value, decimals: int = 3) -> str:
    return f"{float(value):.{decimals}f}" if is_number(value) else "Undefined"


def format_pct(value, decimals: int = 1) -> str:
    return f"{float(value):.{decimals}f}%" if is_number(value) else "Undefined"


def format_metric(m: Metric, kind: str, currency: str = "INR", unit: str = "units") -> str:
    """kind: 'money' | 'index' | 'pct'."""
    if m.status == UNDEFINED or (m.value is None and m.status != NOT_APPLICABLE):
        return "Undefined"
    if m.status == NOT_APPLICABLE:
        return "N/A"
    if kind == "money":
        txt = format_money(m.value, currency, unit)
    elif kind == "pct":
        txt = format_pct(m.value)
    else:
        txt = format_index(m.value)
    return txt + (" ⚠" if m.status == REVIEW else "")
