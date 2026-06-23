import re
import sys
import types
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")

    class _SessionState(dict):
        def __getattr__(self, name):
            return self.get(name)

    streamlit_stub.session_state = _SessionState()
    streamlit_stub.error = lambda *args, **kwargs: None
    streamlit_stub.exception = lambda *args, **kwargs: None
    sys.modules["streamlit"] = streamlit_stub

from app_modules.itinerary_html import build_itinerary_html
from generator import group_rows_by_day
from itinerary_generation.content_validator import compact_html
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows

FIXTURE = ROOT / "tests" / "fixtures" / "activity_training" / "norway_coastal_cruise_transfer_inputs.txt"


def _fixture_inputs() -> dict[str, str]:
    text = FIXTURE.read_text(encoding="utf-8")
    parts = re.split(r"^###\s+(INPUT\s+\d+)\s*$", text, flags=re.MULTILINE)
    return {
        parts[index].strip(): parts[index + 1].strip()
        for index in range(1, len(parts), 2)
        if parts[index + 1].strip()
    }


def _rows_and_html(raw: str):
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    html = build_itinerary_html(rows, group_rows_by_day(rows), {"days": {}, "pictures_added": False})
    return rows, html, compact_html(html)


def _find_row(rows, title_fragment: str):
    fragment = title_fragment.lower()
    for row in rows:
        source = " ".join(str(row.get(key, "") or "") for key in ("title", "original_title", "details"))
        if fragment in source.lower():
            return row
    raise AssertionError(f"Could not find row containing {title_fragment!r}")


def test_uploaded_norway_training_inputs_are_bundled():
    inputs = _fixture_inputs()

    assert set(inputs) == {"INPUT 1", "INPUT 2", "INPUT 3"}
    assert all("Atlantic Coastal Cruise Transfer to Bergen" in raw for raw in inputs.values())
    assert all("Criuse" in raw for raw in inputs.values())


def test_criuse_row_type_preserves_cruise_timing_and_route_in_all_uploaded_inputs():
    for name, raw in _fixture_inputs().items():
        rows, _, plain = _rows_and_html(raw)
        cruise = _find_row(rows, "Atlantic Coastal Cruise Transfer to Bergen")

        assert cruise["type"] == "Cruise", name
        assert cruise["effective_type"] == "Cruise", name
        assert cruise["city"] == "Stavanger", name
        assert cruise["time"] == "7:30 AM - 1:00 PM", name
        assert cruise["meeting_point"] == "Stavanger Cruise Port", name
        assert cruise["route_origin"] == "Stavanger", name
        assert cruise["route_destination"] == "Bergen", name
        assert "missing_route_origin" not in cruise["parser_review_flags"], name
        assert "missing_route_destination" not in cruise["parser_review_flags"], name

        assert "7:30 AM - 1:00 PM" in plain, name
        assert "Criuse" not in plain, name
        assert "Crusie" not in plain, name


def test_coach_input_type_does_not_become_the_city():
    rows, _, plain = _rows_and_html(_fixture_inputs()["INPUT 1"])
    coach = _find_row(rows, "Coach Transfer to Kristiansand")

    assert coach["type"] == "Transport"
    assert coach["effective_type"] == "Transport"
    assert coach["city"] == "Oslo"
    assert coach["time"] == "10:30 AM - 2:48 PM"
    assert coach["route_origin"] == "Oslo"
    assert coach["route_destination"] == "Kristiansand"
    assert "DAY 3 ✦ COACH" not in plain


def test_inclusion_pagination_keeps_private_transfers_off_bottom_of_first_page():
    _, html, _ = _rows_and_html(_fixture_inputs()["INPUT 1"])
    soup = BeautifulSoup(html, "html.parser")
    inclusion_pages = soup.select(".categorized-inclusions-page")
    assert len(inclusion_pages) >= 2

    first_page_sections = [section.get_text(" ", strip=True) for section in inclusion_pages[0].select(".section-title")]
    second_page_sections = [section.get_text(" ", strip=True) for section in inclusion_pages[1].select(".section-title")]

    assert "Private transfers" not in first_page_sections
    assert "Private transfers" in second_page_sections
