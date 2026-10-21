"""
Produce the Manual-vs-Dashboard comparison table for the validation report.

    python benchmark/compare_with_dashboard.py

Writes reports/benchmark_comparison.csv and reports/benchmark_comparison.md.
Manual values: benchmark/benchmark_expected.csv (independent; no app code).
Dashboard values: the real upload pipeline run on data/benchmark_case_work_packages.csv.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tests.test_benchmark import comparison_table  # noqa: E402

LABEL = {"A_CPI": "A", "B_CPI_SPI": "B", "C_BUDGET_RATE": "C", "": ""}


def fmt(v, kind):
    if kind == "money":
        return f"{v:,.4f}"
    return f"{v:.10f}" if kind == "index" else f"{v:.8f}"


def main():
    frames = {m: comparison_table(m) for m in ("work_package", "precalc", "progress")}
    df = frames["work_package"]
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    df.to_csv(os.path.join(ROOT, "reports", "benchmark_comparison.csv"), index=False)
    lines = ["| Metric | Method | Period | Manual result | Dashboard result | Difference | Tolerance | Status |",
             "|---|---|---|---:|---:|---:|---:|---|"]
    for r in df.itertuples():
        lines.append(f"| {r.metric} | {LABEL[r.method]} | {r.period} | {fmt(r.manual, r.kind)} | "
                     f"{fmt(r.dashboard, r.kind)} | {r.difference:.2e} | {r.tolerance:g} | {r.result} |")
    summary = [f"- **{m}** input mode: {len(f)} values compared, {int((f.result == 'PASS').sum())} PASS, "
               f"{int((f.result != 'PASS').sum())} FAIL; max |difference| = {f.difference.abs().max():.2e}"
               for m, f in frames.items()]
    with open(os.path.join(ROOT, "reports", "benchmark_comparison.md"), "w") as fh:
        fh.write("# Benchmark comparison (generated)\n\n" + "\n".join(summary) + "\n\n"
                 "Table below: work-package input mode (the full upload pipeline).\n\n" + "\n".join(lines) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
