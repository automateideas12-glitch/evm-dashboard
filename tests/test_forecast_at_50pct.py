"""
Forecast test on real data at 50 % physical completion (DSLIB C2014-05, Apartment Building (1), Belgium).

data/real/forecast_test/C2014-05_at_50pct_complete.xlsx : 7 real reports + one INTERPOLATED report at EV = 50 % BAC
data/real/forecast_test/C2014-05_forecast_answer_key.xlsx : expected CPI/SPI/EAC and the real final cost

Proves the dashboard reproduces the answer key at the 50 % point and records how good each forecast was.
"""
from datetime import date
from pathlib import Path

import openpyxl
import pytest

from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping
from src.evm_calculations import compute_results

HERE = Path(__file__).resolve().parents[1] / "data" / "real" / "forecast_test"
FILE = HERE / "C2014-05_at_50pct_complete.xlsx"
KEY = HERE / "C2014-05_forecast_answer_key.xlsx"


@pytest.fixture(scope="module")
def result():
    raw = read_table(FILE.read_bytes(), FILE.name)
    s = ProjectSettings(name="C2014-05 at 50 %", currency="EUR", baseline_start=date(2011, 10, 3),
                        baseline_finish=date(2012, 8, 15), reporting_frequency="Irregular")
    p = prepare(raw, suggest_mapping(list(raw.columns), "work_package"), s, "work_package")
    assert p.ok, p.report.to_frame().to_string()
    return p, compute_results(p.periods, p.bac)


def key_rows():
    ws = openpyxl.load_workbook(KEY, data_only=True)["Forecast check"]
    rows = [r for r in ws.iter_rows(values_only=True)]
    hdr = next(i for i, r in enumerate(rows) if r[0] == "Status point")
    head = rows[hdr]
    out = [dict(zip(head, r)) for r in rows[hdr + 1:] if r[1] is not None and r[2] is not None]
    final = next(r[1] for r in rows if r[0] and str(r[0]).startswith("Actual final cost"))
    return out, final


def test_last_report_is_the_interpolated_50pct_point(result):
    p, res = result
    assert res["reporting_date"].iloc[-1].date() == date(2012, 5, 21)
    assert res["pct_complete"].iloc[-1] == pytest.approx(50.0, abs=1e-3)
    assert p.bac == pytest.approx(532_410.29, abs=0.01)


def test_dashboard_equals_answer_key_at_50pct(result):
    _, res = result
    rows, _ = key_rows()
    k = next(r for r in rows if str(r["Status point"]).startswith("50 %"))
    last = res.iloc[-1]
    for tool, col, tol in (("pv", "PV", 0.01), ("ev", "EV", 0.01), ("ac", "AC", 0.01), ("cpi", "CPI", 1e-6),
                           ("spi", "SPI", 1e-6), ("eac_A_CPI", "EAC A = BAC/CPI", 0.05),
                           ("eac_B_CPI_SPI", "EAC B = AC+(BAC−EV)/(CPI×SPI)", 0.05),
                           ("eac_C_BUDGET_RATE", "EAC C = AC+(BAC−EV)", 0.05)):
        assert last[tool] == pytest.approx(k[col], abs=tol), (tool, last[tool], k[col])


def test_forecast_errors_against_real_final_cost(result):
    _, res = result
    _, final = key_rows()
    last = res.iloc[-1]
    err = {m: last[c] / final - 1 for m, c in (("A", "eac_A_CPI"), ("B", "eac_B_CPI_SPI"), ("C", "eac_C_BUDGET_RATE"))}
    assert err["A"] == pytest.approx(0.0698, abs=5e-4)
    assert err["B"] == pytest.approx(0.3248, abs=5e-4)
    assert err["C"] == pytest.approx(-0.0150, abs=5e-4)
    assert abs(err["C"]) < abs(err["A"]) < abs(err["B"])     # same ordering as the manual check case
