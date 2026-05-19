from pathlib import Path
import asyncio
import subprocess
import sys

from playwright.sync_api import sync_playwright


BROWSER_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]


def setup_windows_event_loop():
    """
    On Windows, Playwright sometimes needs the Proactor event loop
    to launch Chromium correctly.
    """

    if sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass


def install_chromium_if_needed():
    """
    Streamlit Cloud installs the Python Playwright package, but not always the
    Chromium browser binary. This command is safe to run more than once.
    """

    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )
    except Exception:
        # Do not fail here. If Chromium is already installed or if the install
        # command is unavailable, the later launch step will provide the real
        # useful error message.
        pass


def export_html_to_pdf(html_path, pdf_path):
    """
    Converts a standalone HTML file into an A4 PDF using Playwright.
    """

    setup_windows_event_loop()
    install_chromium_if_needed()

    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path).resolve()
    pdf_path.parent.mkdir(exist_ok=True)

    file_url = html_path.as_uri()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=BROWSER_LAUNCH_ARGS,
        )

        page = browser.new_page(
            viewport={
                "width": 794,
                "height": 1123,
            }
        )

        page.goto(file_url, wait_until="networkidle")

        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={
                "top": "0mm",
                "right": "0mm",
                "bottom": "0mm",
                "left": "0mm",
            },
            prefer_css_page_size=True,
        )

        browser.close()

    return pdf_path
