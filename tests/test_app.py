"""
Interface tests with Streamlit's AppTest (runs the real app script headlessly).
File upload and data-editor interaction are not supported by AppTest; those
workflows were tested in a real browser (see reports/validation_report.md §11).

Flow under test: the app opens on a HOME screen (start a project: upload / enter / example);
the analysis dashboard appears only after a project is opened.
"""
import json
import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def fresh():
    return AppTest.from_file(APP, default_timeout=60).run()


def demo():
    at = fresh()
    at.button(key="home_demo").click().run()
    return at


def metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def chart_titles(at):
    return [json.loads(c.proto.spec)["layout"].get("title", {}).get("text") for c in at.get("plotly_chart")]


def table(at, first_col):
    return next(d.value for d in at.dataframe if list(d.value.columns)[0] == first_col)


# ---------------------------------------------------------------- home screen
def test_app_opens_on_home_screen_not_on_a_project():
    at = fresh()
    assert not at.exception
    assert len(at.metric) == 0                       # no analysis before a project is chosen
    assert len(at.tabs) == 0
    assert any("Start a project" in s.value for s in at.subheader)
    assert at.radio(key="how").options[0] == "Upload a file"


def test_home_offers_one_click_examples():
    at = fresh()
    labels = {b.key: b.label for b in at.button}
    assert {"home_manual", "home_demo", "home_real", "home_bench"} <= set(labels)


def test_example_opens_whole_analysis_without_confirmation():
    at = demo()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Overview", "Trends", "Forecasts", "Commentary", "Data"]
    assert metric(at, "CPI (cost efficiency)") == "0.947"
    assert any("Critical" in md.value for md in at.markdown)


def test_example_chosen_in_home_loader_opens_without_confirmation():
    at = fresh()
    at.radio(key="how").set_value("Load a built-in example").run()
    at.radio(key="example").set_value(next(o for o in at.radio(key="example").options if o.startswith("Benchmark"))).run()   # benchmark
    assert len(at.checkbox) == 0                     # nothing to replace yet, so nothing to confirm
    next(b for b in at.button if b.label == "Open example").click().run()
    assert not at.exception
    assert metric(at, "Budget at completion (BAC)") == "₹400.00 lakh"


def test_home_button_is_in_the_top_bar_and_returns_home():
    at = demo()
    assert "top_home" not in [b.key for b in at.sidebar.button]     # visible on the page, not hidden in the sidebar
    at.button(key="top_home").click().run()
    assert len(at.metric) == 0 and len(at.tabs) == 0
    assert any("Start a project" in s.value for s in at.subheader)


def test_manual_entry_from_home_opens_dashboard():
    at = fresh()
    at.radio(key="data_mode").set_value("progress").run()
    at.radio(key="how").set_value("Enter or edit manually").run()
    at.text_input(key="man_progress_name").input("Manual test project").run()
    at.number_input(key="man_progress_bac").set_value(10_000_000.0).run()
    next(b for b in at.button if b.key == "man_btn").click().run()
    assert not at.exception
    assert any("Manual test project" in md.value for md in at.markdown)
    # project-level data has no work packages: the panel says so instead of showing empty tables
    assert any("work-package" in i.value.lower() for i in at.info)


# ---------------------------------------------------------------- performance and problem areas
def test_overview_has_combined_performance_panel():
    at = demo()
    assert any(s.value == "Performance and problem areas" for s in at.subheader)
    titles = chart_titles(at)
    assert "CPI and SPI trend" in titles             # one combined chart ...
    assert "CPI trend" not in titles and "SPI trend" not in titles   # ... not two separate ones


def test_work_package_status_and_top_problems_for_benchmark():
    at = fresh()
    at.button(key="home_bench").click().run()        # opens at the latest date, 28-Feb-2026
    wp = table(at, "Work package")
    assert list(wp["Status"]) == ["Warning", "Critical", "Critical", "Critical"]   # hand-calculated
    assert list(wp["CPI"]) == ["0.952", "0.898", "0.857", "0.667"]
    top = table(at, "Activity")
    assert list(top["Activity"]) == ["WP2 RCC superstructure", "WP3 Masonry and finishes",
                                     "WP1 Substructure", "WP4 MEP services"]
    assert list(top["Main issue"])[:2] == ["Behind schedule", "Behind schedule"]
    assert top.iloc[0]["SV"] == "-₹24.00 lakh"


def test_tables_follow_the_reporting_date():
    at = fresh()
    at.button(key="home_bench").click().run()
    at.selectbox(key="sel_date").set_value(0).run()   # 31-Jan-2026
    wp = table(at, "Work package")
    assert list(wp["Status"])[2] == "Not started"    # WP3 has not started in January


# ---------------------------------------------------------------- existing dashboard behaviour (unchanged)
@pytest.mark.parametrize("method", ["A_CPI", "B_CPI_SPI", "C_BUDGET_RATE", "D_INDEPENDENT"])
def test_every_forecast_method_renders(method):
    at = demo()
    at.selectbox(key="method").set_value(method).run()
    assert not at.exception
    eac = metric(at, "Estimate at completion (EAC)")
    if method == "D_INDEPENDENT":
        assert eac == "N/A"          # no independent ETC supplied: not shown as 0
    else:
        assert eac.startswith("₹")


def test_every_reporting_date_and_unit_renders():
    at = demo()
    for unit in ("units", "crore", "million"):
        at.sidebar.selectbox(key="unit").set_value(unit).run()
        assert not at.exception
    for i in range(9):
        at.selectbox(key="sel_date").set_value(i).run()
        assert not at.exception


def test_load_benchmark_example_requires_confirmation():
    at = demo()
    at.radio(key="how").set_value("Load a built-in example").run()
    at.radio(key="example").set_value(next(o for o in at.radio(key="example").options if o.startswith("Benchmark"))).run()
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
    at = demo()
    at.selectbox(key="method").set_value("D_INDEPENDENT").run()
    at.number_input(key="etc_in_8").set_value(40000000.0).run()
    next(b for b in at.button if b.label == "Apply estimate").click().run()
    assert not at.exception
    # EAC = AC 8,66,02,000 + ETC 4,00,00,000 = 12,66,02,000 = 1,266.02 lakh
    assert metric(at, "Estimate at completion (EAC)") == "₹1,266.02 lakh"


# ---------------------------------------------------------------- top control bar
def test_main_controls_are_on_the_page_not_only_in_the_sidebar():
    at = demo()
    side = [s.key for s in at.sidebar.selectbox]
    assert "sel_date" not in side and "method" not in side
    assert at.selectbox(key="sel_date").value == 8          # latest reporting date by default
    assert at.selectbox(key="method").value == "A_CPI"


# ---------------------------------------------------------------- manual-check case (real data, 4 WPs)
def test_manual_check_case_opens_from_home():
    at = fresh()
    at.button(key="home_manual").click().run()
    assert not at.exception
    assert any("IJzertoren" in md.value for md in at.markdown)
    assert metric(at, "CPI (cost efficiency)") == "0.954"      # 28-Feb-2014, workbook row 6
    assert metric(at, "SPI (schedule efficiency)") == "1.000"
    assert len(table(at, "Work package")) == 4


def test_manual_check_case_at_the_two_benchmark_dates():
    at = fresh()
    at.button(key="home_manual").click().run()
    at.selectbox(key="sel_date").set_value(1).run()            # 30-Nov-2013
    assert (metric(at, "CPI (cost efficiency)"), metric(at, "SPI (schedule efficiency)")) == ("0.755", "0.714")
    assert metric(at, "Estimate at completion (EAC)") == "€284,033"      # workbook: 284,033.47
    at.selectbox(key="sel_date").set_value(2).run()            # 31-Dec-2013
    # CPI = 111,728.57 / 156,594.45 = 0.71349 -> "0.713"
    assert (metric(at, "CPI (cost efficiency)"), metric(at, "SPI (schedule efficiency)")) == ("0.713", "0.521")
    assert metric(at, "Estimate at completion (EAC)") == "€300,520"      # workbook: 300,519.58


def test_manual_check_files_can_be_downloaded_from_home():
    at = fresh()
    labels = [d.label for d in at.get("download_button")]
    assert any("hand-calculation workbook" in lab.lower() for lab in labels)
    assert any("manual check data" in lab.lower() for lab in labels)
