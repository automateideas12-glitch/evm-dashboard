"""Chart presentation: readable axes, colour zones, one-date data, units in hover labels."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.charts import combined_index_chart, cumulative_chart
from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping
from src.evm_calculations import compute_results

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def res():
    path = ROOT / "data" / "real" / "C2015-33_ijzertoren_manual_check_work_packages.csv"
    raw = read_table(path.read_bytes(), path.name)
    p = prepare(raw, suggest_mapping(list(raw.columns), "work_package"),
                ProjectSettings(name="x", currency="EUR"), "work_package")
    return p, compute_results(p.periods, p.bac)


def test_each_reporting_date_is_labelled_once(res):
    p, r = res
    fig = cumulative_chart(r, p.bac, "A_CPI", "EUR", "units", "Monthly", r["reporting_date"].iloc[2],
                           date(2013, 12, 20))
    ticks = [pd.Timestamp(t) for t in fig.layout.xaxis.tickvals]
    assert ticks == list(r["reporting_date"])
    assert len(set(fig.layout.xaxis.ticktext)) == len(ticks)          # no repeated labels


def test_hover_labels_show_the_money_unit(res):
    p, r = res
    fig = cumulative_chart(r, p.bac, "A_CPI", "EUR", "units", "Monthly")
    ev = next(t for t in fig.data if t.name.startswith("EV"))
    assert "EUR" in ev.hovertemplate


def test_index_chart_has_red_amber_green_zones(res):
    _, r = res
    fig = combined_index_chart(r, "Monthly", 1.0, 0.9)
    bands = sorted((round(s.y0, 2), round(s.y1, 2)) for s in fig.layout.shapes if s.type == "rect")
    assert len(bands) == 3
    assert bands[0][1] == 0.9            # red: below critical
    assert bands[1] == (0.9, 1.0)        # amber: between critical and warning
    assert bands[2][0] == 1.0            # green: on or better than plan


def test_single_reporting_date_is_explained_not_drawn_as_an_empty_trend(res):
    p, r = res
    one = r.iloc[[2]].reset_index(drop=True)
    for fig in (cumulative_chart(one, p.bac, "A_CPI", "EUR", "units", "Monthly"),
                combined_index_chart(one, "Monthly", 1.0, 0.9)):
        notes = " ".join(a.text for a in fig.layout.annotations)
        assert "one reporting date" in notes.lower()
        assert len(fig.layout.xaxis.tickvals) == 1
