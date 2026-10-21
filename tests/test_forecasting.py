"""
Forecast tests. Hand-worked base case: BAC 1000, PV 500, EV 400, AC 500
  CPI = 400/500 = 0.8 ; SPI = 400/500 = 0.8
  A: EAC = 1000/0.8 = 1250            ETC = 750   VAC = -250  overrun 25%
  B: EAC = 500 + 600/(0.8*0.8) = 1437.5  ETC = 937.5
  C: EAC = 500 + 600 = 1100           ETC = 600
  D: ETC(user) = 650 -> EAC = 1150
  TCPI_BAC = 600/500 = 1.2 ; TCPI_EAC(A) = 600/750 = 0.8 = CPI ; TCPI_EAC(C) = 1
"""
import pytest

from src import forecasting as fc
from src.evm_calculations import compute_period_metrics
from src.metric import NOT_APPLICABLE, OK, REVIEW, UNDEFINED, Metric

BASE = dict(bac=1000, pv=500, ev=400, ac=500)


@pytest.fixture
def m():
    return compute_period_metrics(**BASE, independent_etc=650)


# 7. each supported forecasting method
@pytest.mark.parametrize("method,eac,etc", [
    ("A_CPI", 1250.0, 750.0),
    ("B_CPI_SPI", 1437.5, 937.5),
    ("C_BUDGET_RATE", 1100.0, 600.0),
    ("D_INDEPENDENT", 1150.0, 650.0),
])
def test_each_method(m, method, eac, etc):
    assert m[f"eac_{method}"].value == pytest.approx(eac)
    assert m[f"etc_{method}"].value == pytest.approx(etc)
    assert m[f"vac_{method}"].value == pytest.approx(1000 - eac)
    assert m[f"overrun_{method}"].value == pytest.approx(eac - 1000)
    assert m[f"overrun_pct_{method}"].value == pytest.approx((eac - 1000) / 1000 * 100)


def test_method_b_is_not_chosen_by_default_and_all_methods_reported(m):
    for k in fc.METHODS:
        assert f"eac_{k}" in m


def test_method_d_not_applicable_without_independent_etc():
    m = compute_period_metrics(**BASE)
    assert m["eac_D_INDEPENDENT"].status == NOT_APPLICABLE
    assert m["etc_D_INDEPENDENT"].value is None
    assert m["vac_D_INDEPENDENT"].value is None


def test_method_d_negative_etc_rejected():
    assert fc.eac_independent(500, -10).status == UNDEFINED


def test_method_b_undefined_when_spi_undefined():
    m = compute_period_metrics(bac=1000, pv=0, ev=0, ac=10)
    assert m["eac_B_CPI_SPI"].status == UNDEFINED


def test_eac_below_bac_gives_positive_vac():
    m = compute_period_metrics(bac=1000, pv=400, ev=500, ac=400)  # CPI 1.25
    assert m["eac_A_CPI"].value == pytest.approx(800)
    assert m["vac_A_CPI"].value == pytest.approx(200)
    assert m["overrun_pct_A_CPI"].value == pytest.approx(-20)


def test_eac_above_bac(m):
    assert m["eac_A_CPI"].value > 1000 and m["vac_A_CPI"].value < 0


def test_negative_etc_flagged_for_review_not_zeroed():
    etc = fc.etc_from_eac(Metric.ok(400), 500)
    assert etc.status == REVIEW and etc.value == pytest.approx(-100)


def test_early_stage_forecast_flagged_for_review():
    m = compute_period_metrics(bac=1000, pv=60, ev=50, ac=60)  # 5% complete
    assert m["eac_A_CPI"].status == REVIEW and m["eac_A_CPI"].available
    assert m["eac_C_BUDGET_RATE"].status == OK   # does not use indices


def test_implausible_eac_flagged():
    m = compute_period_metrics(bac=1000, pv=500, ev=200, ac=900)  # CPI 0.222 -> EAC 4500
    assert m["eac_A_CPI"].status == REVIEW


def test_unknown_method_raises():
    with pytest.raises(ValueError):
        fc.forecast("Z", bac=1, ev=1, ac=1, cpi=Metric.ok(1), spi=Metric.ok(1))


# 8. TCPI under different budget conditions
def test_tcpi_bac_within_budget(m):
    assert m["tcpi_bac"].value == pytest.approx(1.2)


def test_tcpi_eac_identities(m):
    assert m["tcpi_eac_A_CPI"].value == pytest.approx(m["cpi"].value)   # TCPI to BAC/CPI forecast = CPI
    assert m["tcpi_eac_C_BUDGET_RATE"].value == pytest.approx(1.0)      # budget-rate forecast = 1
    assert m["tcpi_eac_B_CPI_SPI"].value == pytest.approx(0.64)         # = CPI x SPI


def test_tcpi_bac_undefined_when_ac_equals_bac():
    t = fc.tcpi_to_bac(1000, 800, 1000)
    assert t.status == UNDEFINED and "no longer possible" in t.note


def test_tcpi_bac_undefined_when_budget_exceeded():
    t = fc.tcpi_to_bac(1000, 800, 1200)
    assert t.status == UNDEFINED and t.value is None   # never a misleading negative number


def test_tcpi_not_applicable_when_no_work_remains():
    assert fc.tcpi_to_bac(1000, 1000, 900).status == NOT_APPLICABLE


def test_overrun_pct_requires_positive_bac():
    assert fc.forecast_overrun_pct(0, Metric.ok(100)).status == UNDEFINED
