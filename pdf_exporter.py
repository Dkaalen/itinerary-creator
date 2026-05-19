from pathlib import Path
import asyncio
import subprocess
import sys

from playwright.sync_api import sync_playwright, Error as PlaywrightError


_BROWSER_READY = False


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


def ensure_playwright_chromium():
    """
    Streamlit Cloud installs the Playwright Python package, but it may not
    automatically download the Chromium browser binary. This installs Chromium
    on demand the first time PDF export is used.
    """

    global _BROWSER_READY

    if _BROWSER_READY:
        return

    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _BROWSER_READY = True
    except subprocess.CalledProcessError as error:
        message = error.stderr or error.stdout or str(error)
        raise RuntimeError(
            "Playwright Chromium could not be installed. "
            "Check Streamlit Cloud logs for the full install error.\n\n"
            f"{message}"
        ) from error


def export_html_to_pdf(html_path, pdf_path):
    """
    Converts a standalone HTML file into an A4 PDF using Playwright.
    """

    setup_windows_event_loop()
    ensure_playwright_chromium()

    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path).resolve()

    pdf_path.parent.mkdir(exist_ok=True)

    file_url = html_path.as_uri()

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
        except PlaywrightError:
            # If Streamlit Cloud wiped the browser cache between runs, try once more.
            global _BROWSER_READY
            _BROWSER_READY = False
            ensure_playwright_chromium()
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
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
