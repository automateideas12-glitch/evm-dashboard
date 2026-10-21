"""
Benchmark validation: dashboard pipeline vs INDEPENDENT expected values.

Expected values come from benchmark/benchmark_expected.csv, produced by
benchmark/independent_benchmark_calc.py, which does not import src/ and uses
exact fractions. They match the paper calculation and the plain-formula
spreadsheet (benchmark/benchmark_workbook.xlsx).

The dashboard side runs the SAME path a user does: read the CSV file ->
map columns -> validate -> derive PV/EV/AC -> calculate.
"""
import os

import pandas as pd
import pytest

from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping
from src.evm_calculations import compute_results

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED = pd.read_csv(os.path.join(ROOT, "benchmark", "benchmark_expected.csv"), dtype={"method": str})
EXPECTED["method"] = EXPECTED["method"].fillna("")

TOL = {"money": 0.01, "index": 1e-9, "pct": 1e-7}   # INR 0.01 = one paisa
KIND = {"BAC": "money", "PV": "money", "EV": "money", "AC": "money", "CV": "money", "SV": "money",
        "EAC": "money", "ETC": "money", "VAC": "money", "OVERRUN": "money",
        "CPI": "index", "SPI": "index", "TCPI_BAC": "index", "TCPI_EAC": "index", "OVERRUN_PCT": "pct"}
COL = {"BAC": "bac", "PV": "pv", "EV": "ev", "AC": "ac", "CV": "cv", "SV": "sv", "CPI": "cpi", "SPI": "spi",
       "TCPI_BAC": "tcpi_bac", "EAC": "eac", "ETC": "etc", "VAC": "vac", "OVERRUN": "overrun",
       "OVERRUN_PCT": "overrun_pct", "TCPI_EAC": "tcpi_eac"}


def dashboard_results(mode: str):
    if mode == "work_package":
        path = os.path.join(ROOT, "data", "benchmark_case_work_packages.csv")
        raw = read_table(open(path, "rb").read(), path)
    elif mode == "precalc":   # same project entered as pre-calculated values (PV/EV/AC from the paper calc)
        raw = pd.DataFrame({"reporting_date": ["2026-01-31", "2026-02-28"], "bac": ["40000000"] * 2,
                            "pv_cumulative": ["14600000", "20800000"], "ev_cumulative": ["12800000", "17600000"],
                            "ac_cumulative": ["13700000", "19200000"]})
    else:                     # project-level percentages: 14.6/40 = 36.5%, 12.8/40 = 32% ...
        raw = pd.DataFrame({"reporting_date": ["2026-01-31", "2026-02-28"], "bac": ["40000000"] * 2,
                            "planned_progress_pct": ["36.5", "52"], "actual_progress_pct": ["32", "44"],
                            "ac_cumulative": ["13700000", "19200000"]})
    p = prepare(raw, suggest_mapping(list(raw.columns), mode), ProjectSettings(name="Benchmark"), mode)
    assert p.ok, p.report.to_frame().to_string()
    return compute_results(p.periods, p.bac)


def comparison_table(mode: str = "work_package") -> pd.DataFrame:
    res = dashboard_results(mode)
    out = []
    for _, e in EXPECTED.iterrows():
        row = res[res["reporting_date"] == pd.Timestamp(e["reporting_date"])].iloc[0]
        col = COL[e["metric"]] + (f"_{e['method']}" if e["method"] else "")
        got = row[col]
        out.append({"metric": e["metric"], "method": e["method"], "period": e["reporting_date"],
                    "manual": e["expected_value"], "dashboard": got, "status_flag": row[f"{col}__status"],
                    "kind": KIND[e["metric"]]})
    df = pd.DataFrame(out)
    df["difference"] = df["dashboard"] - df["manual"]
    df["tolerance"] = df["kind"].map(TOL)
    df["result"] = ["PASS" if abs(d) <= t else "FAIL" for d, t in zip(df["difference"], df["tolerance"])]
    return df


@pytest.mark.parametrize("mode", ["work_package", "precalc", "progress"])
def test_benchmark_all_metrics_match(mode):
    df = comparison_table(mode)
    assert len(df) == 54
    failures = df[df["result"] != "PASS"]
    assert failures.empty, failures.to_string()
    assert (df["status_flag"] == "ok").all()


def test_expected_file_is_independent_of_src():
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "benchmark", "independent_benchmark_calc.py")).read())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            modules.add((node.module or "").split(".")[0])
    assert modules <= {"fractions", "csv", "os"}, modules
