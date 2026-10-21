"""
Interface smoke tests with Streamlit's AppTest (runs the real app script headlessly).
File upload and data-editor interaction are not supported by AppTest; those
workflows were tested in a real browser (see reports/validation_report.md §11).
"""
import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def fresh():
    return AppTest.from_file(APP, default_timeout=60).run()


def metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_app_starts_with_demo_and_no_exceptions():
    at = fresh()
    assert not at.exception
    assert metric(at, "CPI (cost efficiency)") == "0.947"
    assert any("Critical" in md.value for md in at.markdown)


@pytest.mark.parametrize("method", ["A_CPI", "B_CPI_SPI", "C_BUDGET_RATE", "D_INDEPENDENT"])
def test_every_forecast_method_renders(method):
    at = fresh()
    at.sidebar.selectbox[0].set_value(method).run()
    assert not at.exception
    eac = metric(at, "Estimate at completion (EAC)")
    if method == "D_INDEPENDENT":
        assert eac == "N/A"          # no independent ETC supplied: not shown as 0
    else:
        assert eac.startswith("₹")


def test_every_reporting_date_and_unit_renders():
    at = fresh()
    for unit in ("units", "crore", "million"):
        at.sidebar.selectbox[1].set_value(unit).run()
        assert not at.exception
    for i in range(9):
        at.sidebar.selectbox[2].set_value(i).run()
        assert not at.exception


def test_load_benchmark_example_requires_confirmation():
    at = fresh()
    at.radio(key="how").set_value("Load a built-in example").run()
    at.radio(key="example").set_value(at.radio(key="example").options[1]).run()
    btn = next(b for b in at.button if b.label == "Load example")
    assert btn.disabled                      # cannot replace the project without confirming
    at.checkbox(key="ex_conf").check().run()
    next(b for b in at.button if b.label == "Load example").click().run()
    assert not at.exception
    assert metric(at, "Budget at completion (BAC)") == "₹400.00 lakh"
    assert metric(at, "CPI (cost efficiency)") == "0.917"
    assert metric(at, "SPI (schedule efficiency)") == "0.846"
    assert metric(at, "Estimate at completion (EAC)") == "₹436.36 lakh"   # 400 x 192/176


def test_independent_etc_enables_method_d():
    at = fresh()
    at.sidebar.selectbox[0].set_value("D_INDEPENDENT").run()
    at.number_input(key="etc_in_8").set_value(40000000.0).run()
    next(b for b in at.button if b.label == "Apply estimate").click().run()
    assert not at.exception
    # EAC = AC 8,66,02,000 + ETC 4,00,00,000 = 12,66,02,000 = 1,266.02 lakh
    assert metric(at, "Estimate at completion (EAC)") == "₹1,266.02 lakh"
