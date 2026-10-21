"""
Real-browser test of the running dashboard + screenshots for the user manual.
NOT collected by pytest (needs a running server and Playwright + Chromium).

    streamlit run app.py            # in one terminal
    python tests/browser_test_playwright.py
Set CHROME_PATH if Playwright's bundled Chromium is not installed.
"""
import os
import tempfile
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

URL = "http://localhost:8501"
ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "reports" / "screenshots"
SCR = Path(tempfile.gettempdir())
log = []


def note(msg):
    log.append(msg)
    print(msg, flush=True)


def wait_idle(page, t=1.5):
    page.wait_for_timeout(400)
    try:
        page.wait_for_selector('[data-testid="stStatusWidget"]', state="detached", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(int(t * 1000))


def tab(page, name):
    page.get_by_role("tab", name=name, exact=True).click()
    wait_idle(page)


def sign_title(page):
    return page.locator(".sb-title").inner_text()


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
    page = b.new_page(viewport={"width": 1440, "height": 2600})
    page.goto(URL)
    page.wait_for_selector(".sb-title", timeout=60000)
    wait_idle(page, 3)
    note(f"Loaded app; signboard: {page.locator('.signboard').inner_text()!r}")
    page.screenshot(path=SHOTS / "01_overview.png", full_page=True)

    for i, name in enumerate(["Trends", "Forecasts", "Commentary"], start=2):
        tab(page, name)
        page.wait_for_timeout(1500)
        page.screenshot(path=SHOTS / f"0{i}_{name.lower()}.png", full_page=True)
        note(f"Tab {name} rendered")

    # ---------- invalid upload must not replace the project
    bad = SCR / "bad_upload.csv"
    bad.write_text("reporting_date,planned_progress_pct,actual_progress_pct,ac_cumulative,bac\n"
                   "2026-01-31,10,8,90000,1000000\n2026-02-28,120,15,abc,1000000\n2026-02-28,30,,200000,1000000\n")
    tab(page, "Data")
    page.get_by_text("Progress-Based Project Data", exact=True).click()
    wait_idle(page)
    page.locator('input[type="file"]').set_input_files(str(bad))
    wait_idle(page, 3)
    page.get_by_label("Project name *").first.fill("Bad upload test")
    page.keyboard.press("Enter")
    wait_idle(page, 2)
    body = page.locator("section.main, [data-testid='stMain']").first.inner_text()
    ok_bad = "cannot be loaded" in body and page.get_by_role("button", name="Load into dashboard").count() == 0
    note(f"Invalid upload: blocking errors shown & no load button = {ok_bad}")
    page.screenshot(path=SHOTS / "05_invalid_upload.png", full_page=True)
    note(f"Signboard after invalid upload: {sign_title(page)!r}")

    # ---------- valid upload (progress-based sample)
    page.locator('input[type="file"]').set_input_files(str(ROOT / "data" / "sample_project_progress.csv"))
    wait_idle(page, 3)
    page.screenshot(path=SHOTS / "06_upload_validated.png", full_page=True)
    page.get_by_text(re.compile("Replace the project currently shown")).first.click()
    wait_idle(page)
    page.get_by_role("button", name="Load into dashboard").click()
    wait_idle(page, 3)
    note(f"After valid upload: signboard {page.locator('.signboard').inner_text()!r}")
    tab(page, "Overview")
    cpi = page.locator('[data-testid="stMetric"]').filter(has_text="CPI (cost efficiency)").inner_text()
    note(f"Overview CPI after progress-mode upload: {cpi!r}")

    # ---------- manual entry in precalc mode: type the benchmark PV/EV/AC
    tab(page, "Data")
    page.get_by_text("Pre-calculated EVM Data", exact=True).click()
    wait_idle(page)
    page.get_by_text("Enter or edit manually", exact=True).click()
    wait_idle(page, 2)
    page.get_by_label("Project name *").first.fill("Benchmark entered manually")
    page.keyboard.press("Tab")
    wait_idle(page)
    page.get_by_label("BAC * (full amount)").fill("40000000")
    page.keyboard.press("Enter")
    wait_idle(page, 3)
    page.screenshot(path=SHOTS / "07_manual_entry.png", full_page=True)
    body = page.locator("[data-testid='stMain']").first.inner_text()
    note(f"Manual entry validation passed: {'Validation passed' in body}")
    page.get_by_text(re.compile("Replace the project currently shown")).first.click()
    wait_idle(page)
    page.get_by_role("button", name="Load into dashboard").click()
    wait_idle(page, 3)
    tab(page, "Overview")
    for lab in ("CPI (cost efficiency)", "SPI (schedule efficiency)", "Estimate at completion (EAC)",
                "TCPI to finish within BAC"):
        t = page.locator('[data-testid="stMetric"]').filter(has_text=lab).first.inner_text()
        note(f"Manual-entry benchmark -> {t.splitlines()[0]}: {[x for x in t.splitlines() if x.strip()][1]}")

    # ---------- edit a cell in the manual table: AC row 2 -> negative must block loading
    tab(page, "Data")
    grid = page.locator('[data-testid="stDataFrame"]').filter(has_text="AC (cumulative)").first
    grid.scroll_into_view_if_needed()
    box = grid.bounding_box()
    note(f"Editor grid box: {box}")
    ac_x = box["x"] + (843 - 380) + 60          # AC (cumulative) column centre (layout at 1440px width)
    row2_y = box["y"] + 35 + 35 + 17
    page.mouse.click(ac_x, row2_y)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")          # open the cell editor
    page.wait_for_timeout(500)
    page.keyboard.press("Control+A")
    page.keyboard.type("-5")
    page.keyboard.press("Enter")
    page.mouse.click(box["x"] + 5, box["y"] - 40)
    wait_idle(page, 3)
    body = page.locator("[data-testid='stMain']").first.inner_text()
    note(f"After editing a cell to -5: blocking error shown = {'cannot be loaded' in body}; "
         f"negative message = {'negative' in body}")
    page.screenshot(path=SCR / "manual_edit_attempt.png", full_page=True)
    b.close()

(ROOT / "reports" / "browser_test_log.txt").write_text("\n".join(log))
