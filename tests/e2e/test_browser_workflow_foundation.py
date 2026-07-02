"""Real browser coverage for the itinerary/PDF workflow.

These tests are intentionally opt-in because they need Playwright browsers and a
running Streamlit app. They cover the bugs unit tests miss when enabled in CI or
locally.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pytest_playwright")

pytestmark = pytest.mark.browser_e2e

SAMPLE_INPUT = """
Day 1	Arrival	01/10/2026					Oslo	Private Airport to Hotel
Day 1	Hotel	01/10/2026	02/10/2026				Oslo	4Star, Example Hotel, 1xNight, Incl Breakfast
Day 2	Activity	02/10/2026					Oslo	Oslo Fjord Sightseeing Cruise | 10:30 AM | 2 Hr
""".strip()


def test_generate_edit_create_pdf_first_click(e2e_app_url, page):
    page.goto(e2e_app_url, wait_until="networkidle")
    page.get_by_label("Supplier text").fill(SAMPLE_INPUT)
    page.get_by_role("button", name="Generate Agent Itinerary").click()
    page.get_by_text("Create PDF", exact=True).wait_for(timeout=60_000)

    page.get_by_role("button", name="Create PDF").click()
    page.get_by_text("Download PDF", exact=True).wait_for(timeout=90_000)


def test_open_saved_project_then_create_pdf(e2e_app_url, page, tmp_path):
    pytest.skip("Foundation placeholder until a compact saved-project fixture is added.")
