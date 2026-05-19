from pathlib import Path
import asyncio
import os
import shutil
import subprocess
import sys

# IMPORTANT FOR STREAMLIT CLOUD:
# Playwright's Python package can be installed while the Chromium browser binary
# is still missing. We force Chromium into a writable folder inside the app repo,
# then use the same folder when launching the browser.
APP_DIR = Path(__file__).resolve().parent
PLAYWRIGHT_BROWSERS_DIR = APP_DIR / ".playwright-browsers"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS_DIR)

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


BROWSER_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--single-process",
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
    Checks whether Playwright has a Chromium executable available in the
    app-local browser folder.
    """

    if not PLAYWRIGHT_BROWSERS_DIR.exists():
        return False

    executable_names = {
        "chrome",
        "chrome.exe",
        "chrome-headless-shell",
        "chrome-headless-shell.exe",
    }

    for path in PLAYWRIGHT_BROWSERS_DIR.rglob("*"):
        if path.name in executable_names and path.is_file():
            return True

    return False


def install_chromium(force=False):
    """
    Installs Chromium for Playwright into a writable app-local folder.

    This is safe to run more than once. If the browser already exists, it exits
    quickly unless force=True is supplied.
    """

    PLAYWRIGHT_BROWSERS_DIR.mkdir(parents=True, exist_ok=True)

    if force and PLAYWRIGHT_BROWSERS_DIR.exists():
        shutil.rmtree(PLAYWRIGHT_BROWSERS_DIR, ignore_errors=True)
        PLAYWRIGHT_BROWSERS_DIR.mkdir(parents=True, exist_ok=True)

    if not force and chromium_executable_exists():
        return

    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS_DIR)

    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        cwd=str(APP_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Playwright could not install Chromium.\n\n"
            f"Command: {sys.executable} -m playwright install chromium\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    if not chromium_executable_exists():
        raise RuntimeError(
            "Playwright reported that Chromium installed successfully, but no "
            f"Chromium executable was found in {PLAYWRIGHT_BROWSERS_DIR}.\n\n"
            f"Installer output:\n{result.stdout}\n{result.stderr}"
        )


def launch_chromium(playwright):
    """
    Launches Chromium. If Playwright says the executable is missing, install the
    browser and retry once.
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
            install_chromium(force=True)
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
    install_chromium(force=False)

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
