"""
Manual-check case: a REAL project small enough to calculate by hand.

IJzertoren Memorial Square (DSLIB C2015-33, Belgium, 2013-14): 12 activities grouped into 4 work
packages, 5 month-end progress reports, finished 2 months late and 4.8 % over budget.
  data/real/C2015-33_ijzertoren_manual_check_work_packages.csv   -> upload file (Work-Package-Level Data)
  data/manual_check/IJzertoren_manual_check_workbook.xlsx        -> hand calculation with Excel formulas

These tests prove (1) the 4-WP file reproduces ProTrack's recorded EVM values, (2) the hand-calculation
workbook and the dashboard agree on every metric for every period, (3) the case shows every feature.
"""
import math
from datetime import date
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from src.analysis import NOT_STARTED, work_package_status
from src.commentary import CRITICAL, INSUFFICIENT, HealthThresholds, classify
from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping
from src.evm_calculations import compute_results

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "real" / "C2015-33_ijzertoren_manual_check_work_packages.csv"
REF = ROOT / "data" / "real" / "C2015-33_ijzertoren_memorial_square_protrack_reference.csv"
BOOK = ROOT / "data" / "manual_check" / "IJzertoren_manual_check_workbook.xlsx"
TH = HealthThresholds()


@pytest.fixture(scope="module")
def case():
    raw = read_table(CSV.read_bytes(), CSV.name)
    s = ProjectSettings(name="IJzertoren", currency="EUR", baseline_start=date(2013, 10, 14),
                        baseline_finish=date(2013, 12, 20), reporting_frequency="Monthly")
    p = prepare(raw, suggest_mapping(list(raw.columns), "work_package"), s, "work_package")
    assert p.ok, p.report.to_frame().to_string()
    return p, compute_results(p.periods, p.bac)


def sheet(name):
    ws = openpyxl.load_workbook(BOOK, data_only=True)[name]
    rows = list(ws.iter_rows(values_only=True))
    hdr = rows[0]
    return pd.DataFrame([r for r in rows[1:] if r[0] is not None], columns=hdr)


def same(tool, hand, tol):
    """Tool value (NaN when undefined) vs workbook cell (number, or text such as 'Undefined' / 'N/A')."""
    if isinstance(tool, float) and math.isnan(tool):
        return isinstance(hand, str)
    return isinstance(hand, (int, float)) and abs(tool - hand) <= tol


# ---------------------------------------------------------------- the data itself
def test_four_work_packages_five_monthly_reports(case):
    p, res = case
    assert p.wp_detail["activity_id"].nunique() == 4
    assert [d.strftime("%Y-%m-%d") for d in res["reporting_date"]] == \
        ["2013-10-31", "2013-11-30", "2013-12-31", "2014-01-31", "2014-02-28"]
    assert p.bac == pytest.approx(214_417.71, abs=0.01)


def test_reproduces_protrack_recorded_values(case):
    _, res = case
    ref = pd.read_csv(REF)
    # % rounded to 2 decimals for hand calculation. Largest possible effect on PV or EV:
    # 0.005 % x BAC = EUR 10.72 (observed: EUR 3.79). AC is only rounded to cents.
    bound = 0.005 / 100 * 214_417.71 + 4 * 0.005
    for c in ("pv", "ev"):
        assert (res[c] - ref[c.upper()]).abs().max() <= bound, c
    assert (res["ac"] - ref["AC"]).abs().max() <= 4 * 0.005
    assert (res["cpi"] - ref["CPI_protrack"]).abs().max() < 5e-4
    assert (res["spi"] - ref["SPI_protrack"]).abs().max() < 5e-4


# ---------------------------------------------------------------- hand calculation == dashboard
METRICS = {  # workbook column -> (tool column, tolerance)
    "PV": ("pv", 0.01), "EV": ("ev", 0.01), "AC": ("ac", 0.01), "CV": ("cv", 0.01), "SV": ("sv", 0.01),
    "CPI": ("cpi", 1e-9), "SPI": ("spi", 1e-9), "% planned": ("pct_planned", 1e-7),
    "% complete": ("pct_complete", 1e-7), "% spent": ("pct_spent", 1e-7),
    "EAC A": ("eac_A_CPI", 0.01), "EAC B": ("eac_B_CPI_SPI", 0.01), "EAC C": ("eac_C_BUDGET_RATE", 0.01),
    "ETC A": ("etc_A_CPI", 0.01), "ETC B": ("etc_B_CPI_SPI", 0.01), "ETC C": ("etc_C_BUDGET_RATE", 0.01),
    "VAC A": ("vac_A_CPI", 0.01), "VAC B": ("vac_B_CPI_SPI", 0.01), "VAC C": ("vac_C_BUDGET_RATE", 0.01),
    "Overrun % A": ("overrun_pct_A_CPI", 1e-7), "TCPI to BAC": ("tcpi_bac", 1e-9),
    "TCPI to EAC A": ("tcpi_eac_A_CPI", 1e-9), "TCPI to EAC B": ("tcpi_eac_B_CPI_SPI", 1e-9),
    "TCPI to EAC C": ("tcpi_eac_C_BUDGET_RATE", 1e-9),
}


def test_workbook_project_level_equals_dashboard_every_metric_every_period(case):
    _, res = case
    hand = sheet("Project calculation")
    assert len(hand) == len(res) == 5
    for col, (tcol, tol) in METRICS.items():
        for i in range(5):
            assert same(float(res[tcol].iloc[i]), hand[col].iloc[i], tol), (col, i + 1, res[tcol].iloc[i], hand[col].iloc[i])


def test_workbook_health_label_equals_dashboard(case):
    _, res = case
    hand = sheet("Project calculation")
    for i in range(5):
        assert hand["Overall health (method A)"].iloc[i] == classify(res.iloc[i], "A_CPI", TH)["overall"]


def test_workbook_work_package_level_equals_dashboard(case):
    p, res = case
    hand = sheet("Work package calculation")
    for i, d in enumerate(res["reporting_date"]):
        tool = work_package_status(p.wp_detail, d, TH).set_index("activity_id")
        h = hand[hand["Period"] == i + 1].set_index("WP ID")
        for wp in tool.index:
            for col, tcol in (("PV", "pv"), ("EV", "ev"), ("AC", "ac"), ("CV", "cv"), ("SV", "sv"),
                              ("CPI", "cpi"), ("SPI", "spi")):
                assert same(float(tool.loc[wp, tcol]), h.loc[wp, col], 0.01 if len(tcol) == 2 else 1e-9), (i + 1, wp, col)
            assert h.loc[wp, "Status"] == tool.loc[wp, "status"], (i + 1, wp)


def test_workbook_inputs_are_the_upload_file():
    inp = sheet("Inputs")
    csv = pd.read_csv(CSV)
    assert len(inp) == len(csv) == 20
    assert list(inp["Budget"].round(2)) == list(csv["activity_budget"])
    assert list(inp["Actual progress %"].round(2)) == list(csv["actual_progress_pct"])


# ---------------------------------------------------------------- the case shows every feature
def test_case_shows_every_status_and_special_case(case):
    p, res = case
    statuses = set()
    for d in res["reporting_date"]:
        statuses |= set(work_package_status(p.wp_detail, d, TH)["status"])
    assert {NOT_STARTED, INSUFFICIENT, CRITICAL} <= statuses          # WP3/WP4 not started; WP4 early start
    assert res["cpi"].iloc[0] > 1 and res["cpi"].iloc[2] < 0.9        # favourable start, then critical
    assert 50 <= res["pct_complete"].iloc[2] <= 55                     # forecast test point at ~50 %
    assert res["tcpi_bac__status"].iloc[-1] == "not_applicable"       # EV = BAC at completion


def test_forecast_sheet_compares_with_the_real_final_cost():
    fc = sheet("Forecast check")
    assert fc["Actual final cost"].iloc[0] == pytest.approx(224_789.67, abs=0.01)
    p3 = fc[fc["Period"] == 3].iloc[0]
    assert p3["Error A"] == pytest.approx(p3["EAC A"] / 224_789.67 - 1, abs=1e-9)
