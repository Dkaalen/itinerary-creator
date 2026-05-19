from pathlib import Path
import asyncio
import os
import subprocess
import sys
import tempfile

# Streamlit Cloud note:
# The Python "playwright" package does not include the Chromium browser binary.
# We install Chromium at runtime into /tmp, which is writable on Streamlit Cloud.
BROWSER_CACHE_DIR = Path(tempfile.gettempdir()) / "itinerary_playwright_browsers"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_CACHE_DIR)

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


BROWSER_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
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


def chromium_executable_exists():
    """
    Checks whether Playwright has a Chromium executable available in the runtime
    browser cache folder.
    """

    if not BROWSER_CACHE_DIR.exists():
        return False

    executable_names = {
        "chrome",
        "chrome.exe",
        "chrome-headless-shell",
        "chrome-headless-shell.exe",
    }

    for path in BROWSER_CACHE_DIR.rglob("*"):
        if path.name in executable_names and path.is_file():
            return True

    return False


def install_chromium_if_needed():
    """
    Installs the Playwright Chromium browser binary if it is missing.

    This runs only when PDF export is requested, not when the Streamlit app starts.
    The first PDF export on Streamlit Cloud can therefore take a little longer.
    """

    BROWSER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if chromium_executable_exists():
        return

    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_CACHE_DIR)

    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=600,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Playwright could not install Chromium.\n\n"
            f"Command: {sys.executable} -m playwright install chromium\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )


def launch_chromium(playwright):
    """
    Launches Chromium. If the executable is missing, install it and retry once.
    """

    try:
        return playwright.chromium.launch(
            headless=True,
            args=BROWSER_LAUNCH_ARGS,
            chromium_sandbox=False,
        )
    except PlaywrightError as error:
        error_text = str(error).lower()

        if "executable doesn't exist" in error_text or "please run the following command" in error_text:
            install_chromium_if_needed()
            return playwright.chromium.launch(
                headless=True,
                args=BROWSER_LAUNCH_ARGS,
                chromium_sandbox=False,
            )

        raise


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
        browser = launch_chromium(playwright)

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
