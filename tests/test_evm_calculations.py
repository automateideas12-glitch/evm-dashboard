"""Core metric tests. Expected values are hand-worked in the comments."""
import math

import pandas as pd
import pytest

from src.evm_calculations import (compute_period_metrics, compute_results, cost_performance_index,
                                  cost_variance, metric_from_row, schedule_performance_index,
                                  schedule_variance)
from src.metric import NOT_APPLICABLE, OK, UNDEFINED


# 1. favourable cost: EV 110, AC 100 -> CV +10, CPI 1.10
def test_favourable_cost_performance():
    assert cost_variance(110, 100).value == pytest.approx(10)
    assert cost_performance_index(110, 100).value == pytest.approx(1.10)


# 2. unfavourable cost: EV 90, AC 100 -> CV -10, CPI 0.90 (a valid result, status OK)
def test_unfavourable_cost_performance():
    cv, cpi = cost_variance(90, 100), cost_performance_index(90, 100)
    assert cv.value == pytest.approx(-10) and cv.status == OK
    assert cpi.value == pytest.approx(0.90) and cpi.status == OK


# 3. favourable schedule: EV 120, PV 100 -> SV +20, SPI 1.2
def test_favourable_schedule_performance():
    assert schedule_variance(120, 100).value == pytest.approx(20)
    assert schedule_performance_index(120, 100).value == pytest.approx(1.2)


# 4. unfavourable schedule: EV 75, PV 100 -> SV -25, SPI 0.75
def test_unfavourable_schedule_performance():
    assert schedule_variance(75, 100).value == pytest.approx(-25)
    assert schedule_performance_index(75, 100).value == pytest.approx(0.75)


# 5. CPI when AC = 0 is undefined, never 0 or infinity; CV is still defined
def test_cpi_undefined_when_ac_zero():
    m = cost_performance_index(50, 0)
    assert m.status == UNDEFINED and m.value is None and not m.available
    assert "AC is zero" in m.note
    assert cost_variance(50, 0).value == pytest.approx(50)


# 6. SPI when PV = 0 is undefined
def test_spi_undefined_when_pv_zero():
    m = schedule_performance_index(0, 0)
    assert m.status == UNDEFINED and m.value is None
    assert "PV is zero" in m.note


def test_missing_inputs_are_undefined_not_zero():
    for m in (cost_variance(None, 100), cost_performance_index(float("nan"), 100),
              schedule_performance_index(10, None)):
        assert m.status == UNDEFINED and m.value is None


def test_negative_ac_gives_undefined_cpi():
    assert cost_performance_index(10, -5).status == UNDEFINED


def test_zero_earned_value_gives_cpi_zero_but_forecast_undefined():
    m = compute_period_metrics(bac=1000, pv=100, ev=0, ac=50)
    assert m["cpi"].value == 0.0 and m["cpi"].status == OK      # EV/AC = 0 is a real (very bad) index
    assert m["eac_A_CPI"].status == UNDEFINED                     # BAC/0 must not be computed
    assert m["eac_B_CPI_SPI"].status == UNDEFINED
    assert m["eac_C_BUDGET_RATE"].value == pytest.approx(1050)    # 50 + (1000 - 0)


def test_project_completion():
    # Finished: EV = PV = BAC = 1000, AC = 1100
    m = compute_period_metrics(bac=1000, pv=1000, ev=1000, ac=1100)
    assert m["spi"].value == pytest.approx(1.0)
    assert m["eac_A_CPI"].value == pytest.approx(1100)  # BAC/CPI = 1000/(1000/1100)
    assert m["etc_A_CPI"].value == pytest.approx(0, abs=1e-6)
    assert m["tcpi_bac"].status == NOT_APPLICABLE
    assert m["tcpi_eac_A_CPI"].status == NOT_APPLICABLE


def test_compute_results_stores_status_and_never_zero_for_undefined():
    periods = pd.DataFrame({"reporting_date": pd.to_datetime(["2026-01-31", "2026-02-28"]),
                            "pv": [0.0, 100.0], "ev": [0.0, 80.0], "ac": [0.0, 90.0]})
    res = compute_results(periods, 1000)
    first = metric_from_row(res.iloc[0], "cpi")
    assert first.status == UNDEFINED and first.value is None
    assert math.isnan(res.loc[0, "cpi"])  # storage placeholder only
    assert metric_from_row(res.iloc[1], "cpi").value == pytest.approx(80 / 90)
    assert metric_from_row(res.iloc[0], "nonexistent").status == UNDEFINED
