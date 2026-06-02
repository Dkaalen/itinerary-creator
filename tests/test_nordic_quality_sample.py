import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
from itinerary_generation.content_validator import compact_html, validate_html
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


def _render_nordic_sample():
    import ui.day_page_sections as day_page_sections

    day_page_sections.select_day_images_with_overrides = lambda grouped_days, output_edits=None: {}
    day_page_sections.render_day_image_slot = lambda *args, **kwargs: ""

    raw = (ROOT / "tests" / "fixtures" / "real_inputs" / "nordic_quality_sample.txt").read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    return rows, build_itinerary_html(rows, grouped, output_edits={})


def test_nordic_quality_sample_is_a_durable_real_input_fixture():
    rows, html = _render_nordic_sample()
    days = {str(row.get("day")) for row in rows}

    assert len(rows) == 47
    assert "Day 1" in days
    assert "Day 15" in days
    assert not validate_html(html)


def test_nordic_quality_sample_matches_key_quality_target_markers():
    _, html = _render_nordic_sample()
    plain = compact_html(html)
    target_file = ROOT / "tests" / "fixtures" / "quality_targets" / "nordic_outputexample1_markers.txt"
    markers = [line.strip() for line in target_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    for marker in markers:
        assert compact_html(marker) in plain


def test_nordic_quality_sample_cleans_supplier_typos_and_avoids_false_activity_leisure():
    _, html = _render_nordic_sample()
    plain = compact_html(html)
    lower = plain.lower()

    for typo in [
        "Excurssion",
        "transfere",
        "crusie",
        "Chocholate",
        "Desctiption",
        "Krongborg",
        "Rosklide",
        "Nickolas",
    ]:
        assert typo.lower() not in lower

    assert "Kronborg" in plain
    assert "Roskilde" in plain
    assert "St Nicholas" in plain
    assert "Norwegian chocolate" in plain
    assert "A day at leisure in Copenhagen - 22nd of September" not in plain
