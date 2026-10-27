"""
Work-package status, top problem activities and the combined CPI/SPI chart.
Expected values are hand-calculated from data/benchmark_case_work_packages.csv
(the manual-validation case), status date 28-Feb-2026, thresholds 1.00 / 0.90.
"""
import math
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.analysis import NOT_STARTED, problem_activities, work_package_status
from src.charts import combined_index_chart
from src.commentary import CRITICAL, FAVOURABLE, INSUFFICIENT, WARNING, HealthThresholds
from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping
from src.evm_calculations import compute_results

ROOT = Path(__file__).resolve().parents[1]
TH = HealthThresholds()          # 1.00 warning, 0.90 critical
FEB = pd.Timestamp("2026-02-28")
JAN = pd.Timestamp("2026-01-31")


@pytest.fixture(scope="module")
def bench():
    path = ROOT / "data" / "benchmark_case_work_packages.csv"
    raw = read_table(path.read_bytes(), path.name)
    s = ProjectSettings(baseline_start=date(2025, 10, 1), baseline_finish=date(2026, 9, 30))
    p = prepare(raw, suggest_mapping(list(raw.columns), "work_package"), s, "work_package")
    assert p.ok
    return p


# ---------------------------------------------------------------- work-package status
def test_status_table_has_one_row_per_work_package_in_file_order(bench):
    t = work_package_status(bench.wp_detail, FEB, TH)
    assert list(t["activity_id"]) == ["WP1", "WP2", "WP3", "WP4"]
    assert list(t["activity_name"])[:2] == ["Substructure", "RCC superstructure"]


def test_status_table_values_match_hand_calculation(bench):
    t = work_package_status(bench.wp_detail, FEB, TH).set_index("activity_id")
    assert t.loc["WP2", "budget"] == 16_000_000
    assert t.loc["WP2", "pv"] == pytest.approx(11_200_000)
    assert t.loc["WP2", "ev"] == pytest.approx(8_800_000)
    assert t.loc["WP2", "ac"] == pytest.approx(9_800_000)
    assert t.loc["WP2", "cv"] == pytest.approx(-1_000_000)
    assert t.loc["WP2", "sv"] == pytest.approx(-2_400_000)
    assert t.loc["WP1", "cpi"] == pytest.approx(8.0 / 8.4)
    assert t.loc["WP1", "spi"] == pytest.approx(1.0)
    assert t.loc["WP2", "cpi"] == pytest.approx(8.8 / 9.8)
    assert t.loc["WP2", "spi"] == pytest.approx(8.8 / 11.2)
    assert t.loc["WP4", "cpi"] == pytest.approx(2 / 3)


def test_status_uses_the_dashboard_thresholds(bench):
    t = work_package_status(bench.wp_detail, FEB, TH).set_index("activity_id")
    assert t.loc["WP1", "status"] == WARNING        # CPI 0.952: between 0.90 and 1.00
    assert t.loc["WP2", "status"] == CRITICAL       # SPI 0.786
    assert t.loc["WP3", "status"] == CRITICAL
    assert t.loc["WP4", "status"] == CRITICAL


def test_status_follows_threshold_changes(bench):
    loose = HealthThresholds(index_warning_below=0.95, index_critical_below=0.5)
    t = work_package_status(bench.wp_detail, FEB, loose).set_index("activity_id")
    assert t.loc["WP1", "status"] == FAVOURABLE     # 0.952 >= 0.95
    assert t.loc["WP3", "status"] == WARNING        # SPI 0.5 is not below 0.5


def test_work_package_not_yet_started_is_labelled_not_critical(bench):
    t = work_package_status(bench.wp_detail, JAN, TH).set_index("activity_id")
    assert t.loc["WP3", "status"] == NOT_STARTED     # PV = EV = AC = 0 on 31-Jan
    assert math.isnan(t.loc["WP3", "cpi"])


def test_missing_index_is_insufficient_not_favourable():
    det = pd.DataFrame({"reporting_date": [FEB], "activity_id": ["X"], "activity_name": ["x"],
                        "activity_budget": [100.0], "pv_i": [0.0], "ev_i": [10.0], "ac_i": [0.0],
                        "cv_i": [10.0], "sv_i": [10.0]})
    t = work_package_status(det, FEB, TH)
    assert t.iloc[0]["status"] == INSUFFICIENT     # EV without AC or PV: indices undefined


def test_status_totals_equal_project_totals(bench):
    t = work_package_status(bench.wp_detail, FEB, TH)
    row = compute_results(bench.periods, bench.bac).set_index("reporting_date").loc[FEB]
    for c in ("pv", "ev", "ac"):
        assert t[c].sum() == pytest.approx(row[c])
    assert t["budget"].sum() == pytest.approx(bench.bac)


# ---------------------------------------------------------------- top problem activities
def test_problems_ranked_by_worst_of_cv_and_sv(bench):
    top = problem_activities(bench.wp_detail, FEB, n=5)
    assert list(top["activity_id"]) == ["WP2", "WP3", "WP1", "WP4"]
    assert list(top["worst_variance"]) == pytest.approx([-2_400_000, -600_000, -400_000, -200_000])


def test_problems_say_which_variance_is_worst(bench):
    top = problem_activities(bench.wp_detail, FEB, n=5).set_index("activity_id")
    assert top.loc["WP2", "main_issue"] == "Behind schedule"
    assert top.loc["WP1", "main_issue"] == "Over budget"


def test_problems_limited_to_n(bench):
    assert len(problem_activities(bench.wp_detail, FEB, n=2)) == 2


def test_problems_exclude_work_packages_without_negative_variance(bench):
    top = problem_activities(bench.wp_detail, JAN, n=10)
    # 31-Jan: WP3 has not started (no variance) -> not a problem
    assert "WP3" not in set(top["activity_id"])
    assert (top["worst_variance"] < 0).all()


# ---------------------------------------------------------------- combined CPI and SPI chart
def test_combined_chart_has_cpi_and_spi_together(bench):
    res = compute_results(bench.periods, bench.bac)
    fig = combined_index_chart(res, "Monthly", TH.index_warning_below, TH.index_critical_below)
    names = [t.name for t in fig.data]
    assert "CPI" in names and "SPI" in names
    assert fig.layout.title.text == "CPI and SPI trend"
    cpi = next(t for t in fig.data if t.name == "CPI")
    assert list(cpi.y) == pytest.approx(list(res["cpi"]))


def test_combined_chart_marks_the_critical_threshold(bench):
    res = compute_results(bench.periods, bench.bac)
    fig = combined_index_chart(res, "Monthly", 1.0, 0.9)
    ys = {round(s.y0, 3) for s in fig.layout.shapes if s.type == "line"}
    assert {1.0, 0.9} <= ys
