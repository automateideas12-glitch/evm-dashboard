"""
Smart reader: understands real-world spreadsheets/CSVs before validation.

Main fixture tests/fixtures/site_status_sheet.xlsx is the team's own site sheet that the
old upload could not read: a status date in a cell ABOVE the table, two blank rows, the
header on row 4, % stored as fractions with % format, a "Project totals" row, extra
columns (Duration, PV) and NO actual-cost column.
Hand-checked figures (status 28-Feb-2025): BAC 32,40,000 (the sheet's own SUM),
PV 21,11,538.46 (the sheet's own PV total), EV 10,63,500.
"""
from pathlib import Path

import pandas as pd
import pytest

from src.data_processing import ProjectSettings, prepare, suggest_mapping, read_table
from src.evm_calculations import compute_results
from src.smart_reader import (ENTERED_SUFFIX, understand, values_entry_table, with_entered_values,
                              workbook_with_missing_columns)

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tests" / "fixtures" / "site_status_sheet.xlsx"


@pytest.fixture(scope="module")
def site():
    return understand(SITE.read_bytes(), SITE.name)


def csv(text: str) -> bytes:
    return text.strip().encode("utf-8")


# ================================================================ the team's site sheet
def test_finds_header_row_below_title_and_blank_rows(site):
    assert site.header_row == 4
    assert list(site.table.columns)[:2] == ["Activity ID", "Activity"]


def test_reads_status_date_written_above_the_table(site):
    assert site.metadata["status_date"] == pd.Timestamp("2025-02-28")
    col = site.mapping["reporting_date"]
    assert col is not None and "from cell B1" in col
    assert set(site.table[col]) == {pd.Timestamp("2025-02-28")}


def test_detects_work_package_data_without_being_told(site):
    assert site.mode == "work_package"
    assert "Activity ID" in site.mode_reason


def test_maps_columns_by_meaning(site):
    m = site.mapping
    assert m["activity_id"] == "Activity ID"
    assert m["activity_name"] == "Activity"
    assert m["activity_budget"] == "BAC / Activity Budget"
    assert m["planned_progress_pct"] == "Planned % Complete"
    assert m["actual_progress_pct"] == "Actual % Complete"


def test_baseline_dates_are_not_mistaken_for_the_reporting_date(site):
    assert site.mapping["reporting_date"] not in ("Baseline Start", "Baseline Finish")


def test_removes_totals_row(site):
    assert len(site.table) == 12
    assert not site.table["Activity ID"].astype(str).str.contains("total", case=False).any()
    assert any("total" in f.lower() for f in site.fixes)


def test_converts_fraction_percentages_and_says_so(site):
    a04 = site.table.set_index("Activity ID").loc["A04"]
    assert a04["Actual % Complete"] == pytest.approx(75.0)
    assert a04["Planned % Complete"] == pytest.approx(100.0)
    assert any("fraction" in f.lower() for f in site.fixes)


def test_reports_missing_actual_cost(site):
    assert site.missing == ["ac_cumulative"]


def test_row_numbers_point_to_the_real_spreadsheet_rows(site):
    assert site.row_numbers[0] == 5 and site.row_numbers[-1] == 16


def test_every_match_has_confidence_and_reason(site):
    for m in site.matches:
        assert m["confidence"] in ("High", "Medium", "Low")
        assert m["reason"]


def test_entered_actual_cost_completes_the_data_and_matches_the_sheet(site):
    entry = values_entry_table(site, "ac_cumulative")
    assert list(entry.columns) == ["Activity ID", "Activity", "Actual cost to date (cumulative)"]
    assert len(entry) == 12
    entry["Actual cost to date (cumulative)"] = [80000, 125000, 260000, 280000, 240000, 130000,
                                                 0, 0, 0, 0, 0, 0]
    u = with_entered_values(site, "ac_cumulative", entry)
    assert u.missing == []
    assert u.mapping["ac_cumulative"].endswith(ENTERED_SUFFIX)
    p = prepare(u.table, u.mapping, ProjectSettings(name="Site"), u.mode)
    assert p.ok, p.report.to_frame().to_string()
    assert p.bac == pytest.approx(3_240_000)
    row = compute_results(p.periods, p.bac).iloc[-1]
    assert row["pv"] == pytest.approx(2_111_538.4615, abs=0.01)    # the sheet's own PV total
    assert row["ev"] == pytest.approx(1_063_500)
    assert row["ac"] == pytest.approx(1_115_000)


def test_validation_errors_name_the_real_spreadsheet_row(site):
    entry = values_entry_table(site, "ac_cumulative")
    entry["Actual cost to date (cumulative)"] = [80000, 125000, -5, 280000, 240000, 130000, 0, 0, 0, 0, 0, 0]
    u = with_entered_values(site, "ac_cumulative", entry)
    p = prepare(u.table, u.mapping, ProjectSettings(name="Site"), u.mode)
    assert not p.ok
    assert 7 in {i.row for i in p.report.errors}           # A03 sits on row 7 of the sheet


def test_blank_entered_values_are_still_missing(site):
    entry = values_entry_table(site, "ac_cumulative")
    u = with_entered_values(site, "ac_cumulative", entry)
    assert u.missing == ["ac_cumulative"]


def test_download_adds_the_missing_column_for_the_user_to_fill(site):
    import io
    data = workbook_with_missing_columns(site)
    back = pd.read_excel(io.BytesIO(data))          # the blank column the user must fill is there
    assert "Actual cost to date (cumulative)" in back.columns
    assert len(back) == 12 and back["Actual cost to date (cumulative)"].isna().all()
    again = understand(data, "filled.xlsx")
    assert again.mapping["ac_cumulative"] == "Actual cost to date (cumulative)"


# ================================================================ messy CSV files
def test_title_rows_odd_headers_symbols_and_percent_signs():
    data = csv("""
Monthly progress report - G+4 block
Prepared by: site office

Month,Cum. Planned %,Cum. Actual %,Cost to date (Rs),Total Budget
31/01/2026,36.5%,32%,"₹1,37,00,000","4,00,00,000"
28/02/2026,52%,44%,"₹1,92,00,000","4,00,00,000"
""")
    u = understand(data, "report.csv")
    assert u.header_row == 4
    assert u.mode == "progress"
    m = u.mapping
    assert (m["reporting_date"], m["planned_progress_pct"], m["actual_progress_pct"],
            m["ac_cumulative"], m["bac"]) == ("Month", "Cum. Planned %", "Cum. Actual %",
                                              "Cost to date (Rs)", "Total Budget")
    p = prepare(u.table, u.mapping, ProjectSettings(name="x"), u.mode)
    assert p.ok, p.report.to_frame().to_string()
    r = compute_results(p.periods, p.bac).iloc[-1]
    assert r["reporting_date"] == pd.Timestamp("2026-02-28")         # dd/mm/yyyy read correctly
    assert r["ev"] == pytest.approx(0.44 * 40_000_000)
    assert r["ac"] == pytest.approx(19_200_000)


def test_primavera_style_bcws_bcwp_acwp_is_precalculated_data():
    u = understand(csv("""
Data Date,BCWS,BCWP,ACWP,BAC
2026-01-31,14600000,12800000,13700000,40000000
2026-02-28,20800000,17600000,19200000,40000000
"""), "p6.csv")
    assert u.mode == "precalc"
    assert (u.mapping["pv_cumulative"], u.mapping["ev_cumulative"], u.mapping["ac_cumulative"]) == \
        ("BCWS", "BCWP", "ACWP")


def test_semicolon_separated_file():
    u = understand(csv("""
Status date;Planned progress (%);Actual progress (%);Actual cost;BAC
2026-01-31;36.5;32;13700000;40000000
"""), "eu.csv")
    assert u.mode == "progress" and u.mapping["actual_progress_pct"] == "Actual progress (%)"


def test_period_cost_and_cumulative_cost_go_to_the_right_fields():
    u = understand(csv("""
Date,Planned %,Actual %,Actual cost this month,Actual cost to date,BAC
2026-01-31,36.5,32,13700000,13700000,40000000
2026-02-28,52,44,5500000,19200000,40000000
"""), "two_costs.csv")
    assert u.mapping["ac_cumulative"] == "Actual cost to date"
    assert u.mapping["ac_period"] == "Actual cost this month"


def test_lakh_and_crore_amounts_are_converted_and_reported():
    u = understand(csv("""
Reporting date,Planned progress %,Actual progress %,AC,BAC
2026-01-31,36.5,32,137 lakh,4 crore
"""), "words.csv")
    row = u.table.iloc[0]
    assert row["AC"] == pytest.approx(13_700_000) and row["BAC"] == pytest.approx(40_000_000)
    assert any("lakh" in f.lower() for f in u.fixes)


def test_unknown_columns_are_not_guessed():
    u = understand(csv("""
Date,Planned %,Actual %,AC,BAC,Contractor,Weather
2026-01-31,36.5,32,13700000,40000000,ABC Infra,Rain
"""), "extra.csv")
    assert "Contractor" not in u.mapping.values() and "Weather" not in u.mapping.values()
    assert {"Contractor", "Weather"} <= set(u.unused_columns)


def test_bare_percent_complete_is_not_used_as_physical_progress():
    # MS Project '% Complete' is duration-based; the team decided it must be mapped by hand.
    u = understand(csv("""
Date,Planned %,% Complete,AC,BAC
2026-01-31,36.5,32,13700000,40000000
"""), "msp.csv")
    assert u.mapping["actual_progress_pct"] is None
    assert "actual_progress_pct" in u.missing
    assert any("duration" in h.lower() for h in u.hints)


def test_activity_rows_detected_even_with_one_status_date_column():
    u = understand(csv("""
Status Date,WBS Code,Task Name,Budgeted Cost,Planned %,Physical %,Cost Incurred
2026-02-28,1.1,Excavation,250000,100,100,262000
2026-02-28,1.2,Footings,350000,100,75,300000
Grand Total,,,600000,,,562000
"""), "tasks.csv")
    assert u.mode == "work_package"
    assert (u.mapping["activity_id"], u.mapping["activity_name"], u.mapping["activity_budget"],
            u.mapping["actual_progress_pct"], u.mapping["ac_cumulative"]) == \
        ("WBS Code", "Task Name", "Budgeted Cost", "Physical %", "Cost Incurred")
    assert len(u.table) == 2                    # Grand Total row removed
    p = prepare(u.table, u.mapping, ProjectSettings(name="x"), u.mode)
    assert p.ok, p.report.to_frame().to_string()


def test_cover_sheet_is_skipped_and_data_sheet_chosen():
    import io
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        pd.DataFrame({"About": ["Monthly EVM report", "Do not edit"]}).to_excel(xw, sheet_name="Cover", index=False)
        pd.DataFrame({"Reporting date": ["2026-01-31"], "Planned %": [36.5], "Actual %": [32],
                      "AC": [13700000], "BAC": [40000000]}).to_excel(xw, sheet_name="Data", index=False)
    u = understand(bio.getvalue(), "book.xlsx")
    assert u.sheet == "Data" and u.mode == "progress"


def test_forcing_a_data_type_remaps_for_that_type(site):
    u = understand(SITE.read_bytes(), SITE.name, mode="progress")
    assert u.mode == "progress"
    assert u.mapping.get("activity_id") is None


# ================================================================ regression: files that already worked
@pytest.mark.parametrize("name,mode", [
    ("data/sample_project_progress.csv", "progress"),
    ("data/sample_project_evm.csv", "precalc"),
    ("data/sample_project_work_packages.csv", "work_package"),
    ("data/benchmark_case_work_packages.csv", "work_package"),
    ("data/real/C2014-05_apartment_building_work_packages.csv", "work_package"),
    ("data/real/C2013-06_government_office_evm.csv", "precalc"),
])
def test_files_that_worked_before_still_work_the_same(name, mode):
    path = ROOT / name
    u = understand(path.read_bytes(), path.name)
    assert u.mode == mode
    old = {k: v for k, v in suggest_mapping(list(read_table(path.read_bytes(), path.name).columns), mode).items() if v}
    for k, v in old.items():
        assert u.mapping[k] == v, k
    assert u.fixes == [] or all("blank" in f.lower() for f in u.fixes)
    assert prepare(u.table, u.mapping, ProjectSettings(name="x"), u.mode).ok


def test_baseline_dates_never_become_the_reporting_date_even_when_no_status_date_exists():
    u = understand(csv("""
Activity ID,Activity,Baseline Start Date,Baseline Finish Date,Budget,Planned %,Actual %,Actual cost
A1,Excavation,2026-01-05,2026-01-30,250000,100,100,262000
"""), "no_status.csv")
    assert u.mode == "work_package"
    assert u.mapping["reporting_date"] is None
    assert "reporting_date" in u.missing          # the app then asks for the status date


def test_header_alone_is_not_enough_values_must_fit():
    u = understand(csv("""
Reporting date,Actual progress comments,Physical progress %,Planned progress (%),AC,BAC
2026-01-31,Slab casting delayed by rain,32,36.5,13700000,40000000
"""), "comments.csv")
    assert u.mapping["actual_progress_pct"] == "Physical progress %"   # text column rejected by its values
    assert u.mapping["notes"] == "Actual progress comments"
