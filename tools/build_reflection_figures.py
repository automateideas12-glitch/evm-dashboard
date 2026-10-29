"""
Figures for the learnings and reflection report, computed from the manual check case
(IJzertoren Memorial Square, DSLIB C2015-33, 4 work packages) through the dashboard's own engine.

    python tools/build_reflection_figures.py
Writes reports/screenshots/r_forecast_check.png and reports/screenshots/r_wp_cv.png.
"""
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.analysis import work_package_status  # noqa: E402
from src.commentary import HealthThresholds  # noqa: E402
from src.data_processing import ProjectSettings, prepare, read_table, suggest_mapping  # noqa: E402
from src.evm_calculations import compute_results  # noqa: E402

CSV = ROOT / "data" / "real" / "C2015-33_ijzertoren_manual_check_work_packages.csv"
OUT = ROOT / "reports" / "screenshots"
FINAL_COST = 224_789.67          # real final cost (AC at 100 % complete)
INK, MUTED, GRID = "#1f2328", "#5b6170", "#e6e8eb"
A_C, B_C, C_C = "#2a78d6", "#eb6834", "#1baf7a"   # categorical slots 1-3 (validated, light surface)
NEG, POS = "#c4423f", "#2a78d6"                    # diverging poles

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": GRID,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False})


def load():
    raw = read_table(CSV.read_bytes(), CSV.name)
    s = ProjectSettings(name="IJzertoren", currency="EUR", baseline_start=date(2013, 10, 14),
                        baseline_finish=date(2013, 12, 20), reporting_frequency="Monthly")
    p = prepare(raw, suggest_mapping(list(raw.columns), "work_package"), s, "work_package")
    return p, compute_results(p.periods, p.bac)


def forecast_figure(p, res):
    r = res.iloc[:-1]                       # the last report is completion: every method = AC
    x = list(range(len(r)))
    labels = [f"{d:%d %b %Y}\n{c:.0f} % complete" for d, c in zip(r["reporting_date"], r["pct_complete"])]
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
    end = len(r) - 1 + 0.12
    ax.hlines(FINAL_COST / 1000, -0.3, end, color=INK, lw=1.6)
    ax.text(end + 0.05, FINAL_COST / 1000 + 6, "Real final cost 224.8", va="center", fontsize=8.5, color=INK)
    ax.hlines(p.bac / 1000, -0.3, end, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.text(end + 0.05, p.bac / 1000 - 8, "Budget (BAC) 214.4", va="center", fontsize=8.5, color=MUTED)
    for col, name, colour, mk in (("eac_A_CPI", "A  BAC/CPI", A_C, "o"),
                                  ("eac_B_CPI_SPI", "B  CPI×SPI", B_C, "s"),
                                  ("eac_C_BUDGET_RATE", "C  budget rate", C_C, "^")):
        y = r[col] / 1000
        ax.plot(x, y, color=colour, lw=2, marker=mk, ms=6, mec="white", mew=1.2, label=name)
        ax.text(x[2] + 0.1, y.iloc[2], f"{name.split()[0]}  {y.iloc[2]:,.0f}", color=INK, fontsize=8.5, va="center")
    ax.set_xticks(x, labels, fontsize=8)
    ax.set_ylabel("Forecast final cost (EAC), € thousand")
    ax.set_ylim(150, 450)
    ax.set_xlim(-0.3, len(r) - 1 + 1.25)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, ncol=1, fontsize=8.5)
    ax.set_title("Forecasts vs what really happened — manual check case (real data)", loc="left",
                 fontsize=10.5, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "r_forecast_check.png")
    plt.close(fig)


def wp_cv_figure(p, res):
    d = res["reporting_date"].iloc[1]
    t = work_package_status(p.wp_detail, d, HealthThresholds())
    t = t.sort_values("cv", ascending=False)                    # most negative drawn at the top
    names = [f"{i}  {n.split(':')[0]}" for i, n in zip(t["activity_id"], t["activity_name"])]
    fig, ax = plt.subplots(figsize=(7.2, 2.4), dpi=200)
    vals = t["cv"] / 1000
    ax.barh(names, vals, color=[NEG if v < 0 else POS for v in vals], height=0.55)
    ax.axvline(0, color=MUTED, lw=1)
    for i, v in enumerate(vals):
        ax.text(v + (0.6 if v >= 0 else -0.6), i, f"{v:+,.1f}", va="center", ha="left" if v >= 0 else "right",
                fontsize=8.5, color=INK)
    total = res["cv"].iloc[1] / 1000
    ax.set_xlim(-40, 12)
    ax.set_xlabel("Cost variance CV = EV − AC, € thousand")
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.suptitle(f"Cost variance by work package, {d:%d %b %Y} (project CV {total:+,.1f}k)", x=0.01, ha="left",
                 fontsize=10, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "r_wp_cv.png")
    plt.close(fig)


if __name__ == "__main__":
    proj, results = load()
    forecast_figure(proj, results)
    wp_cv_figure(proj, results)
    print("written r_forecast_check.png, r_wp_cv.png")
