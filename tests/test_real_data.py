"""
Real-data validation: three real construction projects from the DSLIB empirical database
(Batselier & Vanhoucke, 2015) converted with tools/convert_dslib.py. The dashboard's PV, EV,
AC, CPI and SPI must reproduce the values recorded by ProTrack (independent EVM software)
for every tracking period, in both work-package and pre-calculated input modes.
"""
import os

import numpy as np
import pandas as pd
import pytest

from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping
from src.evm_calculations import compute_results

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = ["C2014-05_apartment_building", "C2013-06_government_office", "C2013-07_family_residence"]


@pytest.mark.parametrize("project", PROJECTS)
@pytest.mark.parametrize("mode,suffix", [("work_package", "_work_packages.csv"), ("precalc", "_evm.csv")])
def test_real_project_matches_protrack(project, mode, suffix):
    base = os.path.join(ROOT, "data", "real", project)
    ref = pd.read_csv(base + "_protrack_reference.csv")
    raw = read_table(open(base + suffix, "rb").read(), base + suffix)
    p = prepare(raw, suggest_mapping(list(raw.columns), mode),
                ProjectSettings(currency="EUR", reporting_frequency="Irregular"), mode)
    assert p.ok, p.report.to_frame().to_string()
    r = compute_results(p.periods, p.bac)
    t = ref.iloc[:len(r)]
    assert len(r) == len(ref)
    # money: CSV values are rounded to cents, so allow EUR 0.05 accumulated rounding
    for ours, theirs in (("pv", "PV"), ("ev", "EV"), ("ac", "AC")):
        assert np.abs(r[ours].values - t[theirs].values).max() < 0.05, ours
    assert np.abs(r["cpi"].values - t["CPI_protrack"].values).max() < 1e-6
    assert np.abs(r["spi"].values - t["SPI_protrack"].values).max() < 1e-6
