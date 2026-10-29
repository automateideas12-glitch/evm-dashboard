"""
Real-data benchmark: compare the hand-calculation workbook with the dashboard for the manual check case
(IJzertoren Memorial Square, DSLIB C2015-33, 4 work packages), for every reporting date, and write
reports/manual_check_comparison.md and .csv.

    python benchmark/compare_manual_check_case.py

The workbook (data/manual_check/IJzertoren_manual_check_workbook.xlsx) is plain Excel formulas; its cached
values are read here. The dashboard values come from the same path a user follows (CSV -> validation -> engine).
"""
import math
import sys
from datetime import date
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.commentary import HealthThresholds, classify  # noqa: E402
from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping  # noqa: E402
from src.evm_calculations import compute_results  # noqa: E402

CSV = ROOT / "data" / "real" / "C2015-33_ijzertoren_manual_check_work_packages.csv"
BOOK = ROOT / "data" / "manual_check" / "IJzertoren_manual_check_workbook.xlsx"
METRICS = [("PV", "pv", "money"), ("EV", "ev", "money"), ("AC", "ac", "money"), ("CV", "cv", "money"),
           ("SV", "sv", "money"), ("CPI", "cpi", "index"), ("SPI", "spi", "index"),
           ("% complete", "pct_complete", "pct"), ("EAC A", "eac_A_CPI", "money"), ("EAC B", "eac_B_CPI_SPI", "money"),
           ("EAC C", "eac_C_BUDGET_RATE", "money"), ("ETC A", "etc_A_CPI", "money"), ("VAC A", "vac_A_CPI", "money"),
           ("Overrun % A", "overrun_pct_A_CPI", "pct"), ("TCPI to BAC", "tcpi_bac", "index"),
           ("TCPI to EAC A", "tcpi_eac_A_CPI", "index"), ("TCPI to EAC B", "tcpi_eac_B_CPI_SPI", "index")]
TOL = {"money": 0.01, "index": 1e-9, "pct": 1e-7}


def main():
    raw = read_table(CSV.read_bytes(), CSV.name)
    s = ProjectSettings(name="IJzertoren", currency="EUR", baseline_start=date(2013, 10, 14),
                        baseline_finish=date(2013, 12, 20), reporting_frequency="Monthly")
    p = prepare(raw, suggest_mapping(list(raw.columns), "work_package"), s, "work_package")
    res = compute_results(p.periods, p.bac)
    ws = openpyxl.load_workbook(BOOK, data_only=True)["Project calculation"]
    rows = list(ws.iter_rows(values_only=True))
    hand = pd.DataFrame(rows[1:], columns=rows[0])
    out = []
    for i in range(len(res)):
        d = res["reporting_date"].iloc[i].date()
        for label, col, kind in METRICS:
            t, h = float(res[col].iloc[i]), hand[label].iloc[i]
            if math.isnan(t):
                ok, diff, t_s = isinstance(h, str), "", "not a number (" + res[f"{col}__status"].iloc[i] + ")"
            else:
                ok = isinstance(h, (int, float)) and abs(t - h) <= TOL[kind]
                diff, t_s = (f"{t - h:.2e}" if isinstance(h, (int, float)) else "n/a"), f"{t:,.4f}"
            out.append({"Period": i + 1, "Date": d, "Metric": label,
                        "Workbook (manual)": f"{h:,.4f}" if isinstance(h, (int, float)) else h,
                        "Dashboard": t_s, "Difference": diff, "Tolerance": TOL[kind], "Status": "PASS" if ok else "FAIL"})
        out.append({"Period": i + 1, "Date": d, "Metric": "Overall health (A)",
                    "Workbook (manual)": hand["Overall health (method A)"].iloc[i],
                    "Dashboard": classify(res.iloc[i], "A_CPI", HealthThresholds())["overall"], "Difference": "",
                    "Tolerance": "", "Status": "PASS" if hand["Overall health (method A)"].iloc[i] ==
                    classify(res.iloc[i], "A_CPI", HealthThresholds())["overall"] else "FAIL"})
    df = pd.DataFrame(out)
    df.to_csv(ROOT / "reports" / "manual_check_comparison.csv", index=False)
    n_fail = int((df["Status"] == "FAIL").sum())
    md = [f"# Manual check case: workbook vs dashboard (all {len(res)} reporting dates)", "",
          f"{len(df)} values compared, {len(df) - n_fail} PASS, {n_fail} FAIL. Tolerances: money EUR 0.01, "
          "indices 1e-9, percentages 1e-7.", "",
          "| Period | Date | Metric | Workbook (manual) | Dashboard | Difference | Status |",
          "|---|---|---|---:|---:|---:|---|"]
    md += [f"| {r['Period']} | {r['Date']} | {r['Metric']} | {r['Workbook (manual)']} | {r['Dashboard']} | "
           f"{r['Difference']} | {r['Status']} |" for _, r in df.iterrows()]
    (ROOT / "reports" / "manual_check_comparison.md").write_text("\n".join(md) + "\n")
    print(f"{len(df)} compared, {n_fail} failed")
    return n_fail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
