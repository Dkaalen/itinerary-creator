"""Browser E2E fixtures for the Streamlit itinerary workflow."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Iterator

import pytest

APP_URL_ENV = "ITINERARY_E2E_APP_URL"
RUN_E2E_ENV = "ITINERARY_RUN_BROWSER_E2E"


def pytest_configure(config):
    config.addinivalue_line("markers", "browser_e2e: real browser workflow tests")


@pytest.fixture(scope="session")
def e2e_app_url() -> Iterator[str]:
    """Return an existing app URL or start Streamlit for browser tests."""

    explicit_url = os.getenv(APP_URL_ENV)
    if explicit_url:
        yield explicit_url.rstrip("/")
        return

    if os.getenv(RUN_E2E_ENV) != "1":
        pytest.skip(f"Set {RUN_E2E_ENV}=1 or {APP_URL_ENV} to run browser E2E tests.")

    if shutil.which("streamlit") is None:
        pytest.skip("streamlit executable is not available for browser E2E tests.")

    port = int(os.getenv("ITINERARY_E2E_PORT", "8509"))
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(8)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
