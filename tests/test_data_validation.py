"""Input-pipeline tests: parsing, validation, derivation, import/export, display rounding."""
import io

import pandas as pd
import pytest

from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping, template
from src.evm_calculations import compute_results
from src.formatting import format_metric, format_money, format_index, indian_grouping
from src.metric import Metric
from src.validation import ERROR, INFO, WARNING, to_number

S = ProjectSettings(name="Test project", bac=1000.0)


def run(rows: dict, mode="progress", settings=S, first_row=2):
    raw = pd.DataFrame({k: [str(v) if v is not None else "" for v in vals] for k, vals in rows.items()})
    return prepare(raw, suggest_mapping(list(raw.columns), mode), settings, mode, first_row)


def msgs(p, sev):
    return [i.message for i in p.report.issues if i.severity == sev]


GOOD = {"reporting_date": ["2026-01-31", "2026-02-28"], "planned_progress_pct": [10, 20],
        "actual_progress_pct": [8, 15], "ac_cumulative": [90, 170]}


def test_good_progress_data_derives_pv_ev():
    p = run(GOOD)
    assert p.ok
    assert list(p.periods["pv"]) == [100.0, 200.0]
    assert list(p.periods["ev"]) == [80.0, 150.0]
    assert p.value_sources["pv"].startswith("derived")


# 9. missing values are errors, never zero
def test_missing_value_is_error_not_zero():
    rows = dict(GOOD, actual_progress_pct=[8, None])
    p = run(rows)
    assert not p.ok and p.periods is None
    assert any(i.row == 3 and i.field == "actual_progress_pct" for i in p.report.errors)


def test_missing_required_column():
    rows = {k: v for k, v in GOOD.items() if k != "planned_progress_pct"}
    p = run(rows)
    assert any("not mapped" in m for m in msgs(p, ERROR))


def test_missing_actual_cost_column():
    rows = {k: v for k, v in GOOD.items() if k != "ac_cumulative"}
    assert any("Actual cost is missing" in m for m in msgs(run(rows), ERROR))


def test_non_numeric_value_reports_row():
    p = run(dict(GOOD, ac_cumulative=[90, "abc"]))
    e = [i for i in p.report.errors if i.field == "ac_cumulative"]
    assert e and e[0].row == 3 and "not a number" in e[0].message


def test_invalid_date():
    p = run(dict(GOOD, reporting_date=["2026-01-31", "31st Feb"]))
    assert any(i.field == "reporting_date" for i in p.report.errors)


def test_missing_project_name_and_bad_bac():
    assert any("Project name" in m for m in msgs(run(GOOD, settings=ProjectSettings(bac=1000.0)), ERROR))
    assert any("BAC must be greater" in m for m in msgs(run(GOOD, settings=ProjectSettings(name="x", bac=-5.0)), ERROR))
    assert any("BAC is missing" in m for m in msgs(run(GOOD, settings=ProjectSettings(name="x")), ERROR))


# 10. negative values
def test_negative_cumulative_ac_is_error():
    p = run(dict(GOOD, ac_cumulative=[90, -10]))
    assert any("negative" in m for m in msgs(p, ERROR))


def test_negative_period_ac_is_warning_only():
    rows = {k: v for k, v in GOOD.items() if k != "ac_cumulative"}
    rows["ac_period"] = [90, -5]
    p = run(rows)
    assert p.ok and any("Period AC is negative" in m for m in msgs(p, WARNING))


# 11. invalid percentages
@pytest.mark.parametrize("bad", [120, -3])
def test_progress_out_of_range(bad):
    p = run(dict(GOOD, planned_progress_pct=[10, bad]))
    assert not p.ok and any("outside the allowed 0–100%" in m for m in msgs(p, ERROR))


def test_fraction_style_percentages_warn_but_are_not_converted():
    p = run(dict(GOOD, planned_progress_pct=[0.1, 0.2], actual_progress_pct=[0.08, 0.15]))
    assert any("≤ 1" in m for m in msgs(p, WARNING))
    assert p.periods["pv"].iloc[1] == pytest.approx(2.0)  # 0.2% of 1000, not silently x100


def test_percent_sign_accepted_for_pct_but_not_money():
    assert to_number("45%", allow_percent_sign=True) == (45.0, None)
    assert to_number("45%", allow_percent_sign=False)[1] is not None
    assert to_number("₹1,25,000")[0] == 125000.0
    assert to_number("(1,000)")[0] == -1000.0


# 12. cumulative inconsistencies
def test_decreasing_cumulative_progress_warns_and_keeps_value():
    p = run(dict(GOOD, actual_progress_pct=[8, 6]))
    assert p.ok and any("decreases" in m for m in msgs(p, WARNING))
    assert p.periods["actual_pct"].iloc[1] == 6.0


def test_cost_without_progress_is_not_an_error():
    p = run(dict(GOOD, actual_progress_pct=[8, 8]))
    assert p.ok and not any("decreases" in m for m in msgs(p, WARNING))


def test_cumulative_and_period_ac_inconsistent():
    rows = dict(GOOD, ac_period=[90, 50])  # cumulative rose by 80, period says 50
    p = run(rows)
    assert p.ok and any("Inconsistent cost data" in m for m in msgs(p, WARNING))
    assert list(p.periods["ac"]) == [90.0, 170.0]  # cumulative used, NOT 90+170 or a sum


def test_period_ac_only_is_derived_as_running_total():
    rows = {k: v for k, v in GOOD.items() if k != "ac_cumulative"}
    rows["ac_period"] = [90, 80]
    p = run(rows)
    assert list(p.periods["ac"]) == [90.0, 170.0]
    assert p.value_sources["ac"].startswith("derived")


# 13. ordering of reporting dates
def test_unsorted_dates_are_sorted_with_info():
    rows = {k: list(reversed(v)) for k, v in GOOD.items()}
    p = run(rows)
    assert p.ok and list(p.periods["reporting_date"]) == sorted(p.periods["reporting_date"])
    assert any("sorted chronologically" in m for m in msgs(p, INFO))
    assert list(p.periods["source_row"]) == [3, 2]  # traceable to original rows


def test_duplicate_dates_are_errors():
    p = run(dict(GOOD, reporting_date=["2026-01-31", "2026-01-31"]))
    assert any("Duplicate" in m for m in msgs(p, ERROR))


def test_missing_monthly_period_and_baseline_range_warn():
    s = ProjectSettings(name="x", bac=1000.0, baseline_start=pd.Timestamp("2026-02-01").date(),
                        baseline_finish=pd.Timestamp("2026-03-31").date())
    p = run(dict(GOOD, reporting_date=["2026-01-31", "2026-04-30"]), settings=s)
    w = msgs(p, WARNING)
    assert any("missing" in m for m in w)
    assert any("before the baseline start" in m for m in w)
    assert any("after the baseline completion" in m for m in w)


def test_progress_mode_does_not_use_supplied_pv_columns():
    p = run(dict(GOOD, PV=[999, 999]))
    assert p.periods["pv"].iloc[0] == 100.0
    assert any("NOT used" in m for m in msgs(p, WARNING))


def test_unknown_and_duration_percent_columns_not_interpreted():
    raw_cols = ["reporting_date", "% Complete", "Planned_progress_pct", "ac_cumulative", "Mystery"]
    m = suggest_mapping(raw_cols, "progress")
    assert m["actual_progress_pct"] is None   # MS Project duration % is NOT auto-mapped
    assert "Mystery" not in m.values()


def test_precalc_mode_uses_supplied_values_and_checks_ev_le_bac():
    rows = {"reporting_date": ["2026-01-31"], "pv_cumulative": [300], "ev_cumulative": [250],
            "ac_cumulative": [260]}
    p = run(rows, mode="precalc")
    assert p.ok and p.periods["ev"].iloc[0] == 250 and p.value_sources["ev"] == "supplied"
    bad = run(dict(rows, ev_cumulative=[1500]), mode="precalc")
    assert any("exceeds BAC" in m for m in msgs(bad, ERROR))


def test_bac_column_conflicts():
    p = run(dict(GOOD, bac=[1000, 1200]), settings=ProjectSettings(name="x"))
    assert any("BAC changes between rows" in m for m in msgs(p, ERROR))
    p2 = run(dict(GOOD, bac=[2000, 2000]), settings=S)
    assert any("differs from BAC in project settings" in m for m in msgs(p2, ERROR))


# work-package mode
WP = {"reporting_date": ["2026-01-31", "2026-01-31", "2026-02-28", "2026-02-28"],
      "activity_id": ["A", "B", "A", "B"], "activity_budget": [100, 300, 100, 300],
      "planned_progress_pct": [50, 10, 100, 30], "actual_progress_pct": [50, 0, 100, 20],
      "ac_cumulative": [55, 5, 105, 70]}


def test_work_package_ev_is_budget_weighted_not_simple_average():
    p = run(WP, mode="work_package", settings=ProjectSettings(name="x"))
    assert p.ok and p.bac == 400
    # Feb: EV = 100*1.00 + 300*0.20 = 160 ; the unweighted mean (60%) x 400 would wrongly give 240
    assert p.periods["ev"].iloc[1] == pytest.approx(160)
    assert p.periods["actual_pct"].iloc[1] == pytest.approx(40)


def test_work_package_missing_record_is_error():
    rows = {k: v[:3] for k, v in WP.items()}
    p = run(rows, mode="work_package", settings=ProjectSettings(name="x"))
    assert not p.ok and any("no record" in m for m in msgs(p, ERROR))


def test_work_package_budget_change_and_bac_reconciliation():
    rows = dict(WP, activity_budget=[100, 300, 120, 300])
    assert any("changes between dates" in m for m in msgs(run(rows, "work_package", ProjectSettings(name="x")), ERROR))
    p = run(WP, "work_package", ProjectSettings(name="x", bac=500.0))
    assert p.ok and any("may not cover the whole project" in m for m in msgs(p, WARNING))


# 14. rounding and display (display only — values are never rounded in calculations)
def test_display_formatting():
    assert indian_grouping(40000000) == "4,00,00,000"
    assert indian_grouping(-1234567) == "-12,34,567"
    assert format_money(46906445.3125) == "₹4,69,06,445"
    assert format_money(46906445.3125, unit="lakh") == "₹469.06 lakh"
    assert format_money(46906445.3125, unit="crore") == "₹4.69 cr"
    assert format_money(-900000, currency="USD") == "-$900,000"
    assert format_money(None) == "Undefined"
    assert format_index(0.9343065693) == "0.934"
    assert format_metric(Metric.undefined("x"), "index") == "Undefined"
    assert format_metric(Metric.not_applicable("x"), "index") == "N/A"
    assert format_metric(Metric.review(1.5, "x"), "index") == "1.500 ⚠"


def test_calculations_not_rounded():
    p = run(GOOD)
    r = compute_results(p.periods, p.bac)
    assert r["cpi"].iloc[0] == 80 / 90  # full precision retained


# 15. CSV / Excel import and export
@pytest.mark.parametrize("mode", ["progress", "precalc", "work_package"])
def test_templates_import_cleanly(mode):
    buf = io.BytesIO()
    template(mode).to_csv(buf, index=False)
    raw = read_table(buf.getvalue(), "t.csv")
    p = prepare(raw, suggest_mapping(list(raw.columns), mode), ProjectSettings(name="T"), mode)
    assert p.ok, p.report.to_frame()


def test_excel_roundtrip_and_blank_rows_skipped():
    df = template("precalc")
    buf = io.BytesIO()
    pd.concat([df, pd.DataFrame([{}])]).to_excel(buf, index=False)  # trailing blank row
    raw = read_table(buf.getvalue(), "t.xlsx")
    p = prepare(raw, suggest_mapping(list(raw.columns), "precalc"), ProjectSettings(name="T"), "precalc")
    assert p.ok and len(p.periods) == 2


def test_unsupported_file_type():
    with pytest.raises(ValueError):
        read_table(b"x", "data.pdf")


def test_results_export_roundtrip():
    p = run(GOOD)
    r = compute_results(p.periods, p.bac)
    buf = io.StringIO()
    r.to_csv(buf, index=False)
    back = pd.read_csv(io.StringIO(buf.getvalue()))
    assert back["cpi"].iloc[1] == pytest.approx(r["cpi"].iloc[1], rel=1e-12)
    assert back["cpi__status"].iloc[0] == "ok"


def test_manual_entry_and_upload_give_identical_results():
    """Same inputs via a manual-entry table (typed values, row numbering from 1) and via a CSV upload."""
    manual = pd.DataFrame({"reporting_date": pd.to_datetime(GOOD["reporting_date"]),
                           "planned_progress_pct": [10.0, 20.0], "actual_progress_pct": [8.0, 15.0],
                           "ac_cumulative": [90.0, 170.0]})
    pm = prepare(manual, {c: c for c in manual.columns}, S, "progress", first_data_row=1)
    buf = io.BytesIO()
    pd.DataFrame(GOOD).to_csv(buf, index=False)
    raw = read_table(buf.getvalue(), "u.csv")
    pu = prepare(raw, suggest_mapping(list(raw.columns), "progress"), S, "progress")
    rm, ru = compute_results(pm.periods, pm.bac), compute_results(pu.periods, pu.bac)
    num = [c for c in rm.columns if "__" not in c and c != "reporting_date"]
    pd.testing.assert_frame_equal(rm[num], ru[num])


def test_activity_file_in_project_mode_gives_one_clear_error():
    """An activity-level file uploaded as project-level data must not be read as one period per row."""
    rows = dict(WP, activity_name=["Found", "Frame", "Found", "Frame"])
    for mode in ("progress", "precalc"):
        p = run(rows, mode=mode)
        assert not p.ok and p.periods is None
        assert len(p.report.errors) == 1 and not p.report.warnings
        assert "Work-Package-Level Data" in p.report.errors[0].fix
    assert run(WP, mode="work_package", settings=ProjectSettings(name="x")).ok
