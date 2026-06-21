"""Dev tool: screenshot the running Streamlit app once it has actually rendered.

Streamlit renders client-side over a websocket, so a naive headless screenshot grabs
skeleton loaders. This waits for real content (a rendered Plotly chart) before shooting.

Usage:  .venv/bin/python scripts/shoot.py [url] [out.png]
Defaults: http://localhost:8521/  ->  /tmp/sreca_shot.png
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright


def shoot(url: str, out: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        page.goto(url, wait_until="networkidle", timeout=60_000)
        # Real content: Streamlit renders Plotly as an <svg class="main-svg">.
        page.wait_for_selector("svg.main-svg", timeout=60_000)
        page.wait_for_timeout(1500)  # let layout + fonts settle
        page.screenshot(path=out, full_page=True)
        browser.close()
    print(f"shot -> {out}")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8521/"
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/sreca_shot.png"
    shoot(url, out)
