"""
The Metric result type shared by every calculation.

Why not just return a float?
    An EVM index can be mathematically undefined (CPI when AC = 0) or not
    applicable (TCPI when no work remains). Returning 0 or NaN would let an
    undefined value be displayed, charted or averaged as if it were a real
    number. A Metric always carries an explicit status and a human-readable
    reason, so the interface can show "Undefined - AC is zero" instead of 0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

OK = "ok"                      # valid number
REVIEW = "review"              # number is computed but is implausible / needs review
UNDEFINED = "undefined"        # cannot be calculated (zero/negative denominator, missing input)
NOT_APPLICABLE = "not_applicable"  # concept does not apply (e.g. TCPI when no work remains)

ZERO_TOL = 1e-9  # money values below this magnitude are treated as zero


@dataclass(frozen=True)
class Metric:
    value: Optional[float]
    status: str = OK
    note: str = ""

    @property
    def available(self) -> bool:
        """True when a number exists that may be displayed (OK or REVIEW)."""
        return self.value is not None and self.status in (OK, REVIEW)

    @staticmethod
    def ok(value: float, note: str = "") -> "Metric":
        return Metric(float(value), OK, note)

    @staticmethod
    def review(value: float, note: str) -> "Metric":
        return Metric(float(value), REVIEW, note)

    @staticmethod
    def undefined(note: str) -> "Metric":
        return Metric(None, UNDEFINED, note)

    @staticmethod
    def not_applicable(note: str) -> "Metric":
        return Metric(None, NOT_APPLICABLE, note)


def is_number(x) -> bool:
    """A real, finite number (rejects None, NaN, inf, strings, booleans)."""
    if x is None or isinstance(x, bool):
        return False
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(xf)


def is_zero(x: float) -> bool:
    return abs(x) < ZERO_TOL
