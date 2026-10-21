"""
Independent benchmark calculation for the CE 725 EVM Dashboard.

PURPOSE
    Produce the expected ("manual") results for the benchmark case WITHOUT
    using any code from the dashboard (nothing is imported from src/).
    Every formula is written out inline, in the same order a person would
    work it on paper, using exact rational arithmetic (fractions.Fraction)
    so that no floating-point rounding enters the expected values.

    This script is a cross-check of the paper calculation shown in
    reports/validation_report.md, Section 4. The Validation Engineer should
    still redo the paper calculation independently and sign it off.

RUN
    python benchmark/independent_benchmark_calc.py
    -> prints the working and writes benchmark/benchmark_expected.csv
"""
from fractions import Fraction as F
import csv
import os

# ---------------------------------------------------------------- inputs
# Illustrative G+4 RCC residential block. All money in Indian rupees (INR).
# Work-package budgets (approved baseline):
BUDGET = {
    "WP1 Substructure": F(8_000_000),
    "WP2 RCC superstructure": F(16_000_000),
    "WP3 Masonry and finishes": F(12_000_000),
    "WP4 MEP services": F(4_000_000),
}
BAC = sum(BUDGET.values())  # 40,000,000

# Cumulative planned %, actual physical %, cumulative actual cost per WP
PERIODS = {
    "2026-01-31": {
        "WP1 Substructure":          (100, 100, 8_400_000),
        "WP2 RCC superstructure":    (40,  30,  5_200_000),
        "WP3 Masonry and finishes":  (0,   0,   0),
        "WP4 MEP services":          (5,   0,   100_000),
    },
    "2026-02-28": {
        "WP1 Substructure":          (100, 100, 8_400_000),
        "WP2 RCC superstructure":    (70,  55,  9_800_000),
        "WP3 Masonry and finishes":  (10,  5,   700_000),
        "WP4 MEP services":          (10,  5,   300_000),
    },
}


def dec(x, places=10):
    """Exact Fraction -> decimal string (for display/CSV only)."""
    return f"{float(x):.{places}f}" if x is not None else ""


rows = []
print(f"BAC = sum of WP budgets = {BAC:,}")
for date, wps in PERIODS.items():
    print("\n" + "=" * 70 + f"\nReporting date {date}")
    pv = ev = ac = F(0)
    for wp, (pp, ap, cost) in wps.items():
        b = BUDGET[wp]
        pv_i = b * F(pp, 100)
        ev_i = b * F(ap, 100)
        print(f"  {wp:28s} budget {b:>12,}  PV_i = {b:,} x {pp}% = {pv_i:>12,}"
              f"  EV_i = {b:,} x {ap}% = {ev_i:>12,}  AC_i = {cost:,}")
        pv += pv_i
        ev += ev_i
        ac += F(cost)
    cv = ev - ac
    sv = ev - pv
    cpi = ev / ac
    spi = ev / pv
    eac_a = BAC / cpi                              # Method A
    eac_b = ac + (BAC - ev) / (cpi * spi)          # Method B
    eac_c = ac + (BAC - ev)                        # Method C
    tcpi_bac = (BAC - ev) / (BAC - ac)
    print(f"  PV={pv:,}  EV={ev:,}  AC={ac:,}")
    print(f"  CV = EV-AC = {cv:,};  SV = EV-PV = {sv:,}")
    print(f"  CPI = {ev}/{ac} = {dec(cpi)};  SPI = {ev}/{pv} = {dec(spi)}")
    print(f"  TCPI_BAC = ({BAC}-{ev})/({BAC}-{ac}) = {dec(tcpi_bac)}")
    base = {"BAC": BAC, "PV": pv, "EV": ev, "AC": ac, "CV": cv, "SV": sv,
            "CPI": cpi, "SPI": spi, "TCPI_BAC": tcpi_bac}
    for k, v in base.items():
        rows.append((date, k, "", v))
    for m, eac in (("A_CPI", eac_a), ("B_CPI_SPI", eac_b), ("C_BUDGET_RATE", eac_c)):
        etc = eac - ac
        vac = BAC - eac
        over = eac - BAC
        over_pct = over / BAC * 100
        tcpi_eac = (BAC - ev) / (eac - ac)
        print(f"  Method {m:14s} EAC={dec(eac,4):>18} ETC={dec(etc,4):>18} "
              f"VAC={dec(vac,4):>18} overrun%={dec(over_pct,6)} TCPI_EAC={dec(tcpi_eac)}")
        for k, v in (("EAC", eac), ("ETC", etc), ("VAC", vac),
                     ("OVERRUN", over), ("OVERRUN_PCT", over_pct), ("TCPI_EAC", tcpi_eac)):
            rows.append((date, k, m, v))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_expected.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["reporting_date", "metric", "method", "expected_value", "exact_fraction"])
    for date, k, m, v in rows:
        w.writerow([date, k, m, dec(v, 10), f"{v.numerator}/{v.denominator}"])
print(f"\nWrote {len(rows)} expected values to {out}")
