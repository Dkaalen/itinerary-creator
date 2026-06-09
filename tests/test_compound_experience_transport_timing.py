import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _visual_editor_frontend_source() -> str:
    frontend = ROOT / "visual_editor_component" / "frontend"
    parts = [(frontend / "index.html").read_text(encoding="utf-8")]
    for relative in (
        "styles/editor.css",
        "js/state.js",
        "js/images.js",
        "js/render.js",
        "js/serialization.js",
        "js/commands.js",
        "js/editing.js",
        "js/streamlit_bridge.js",
    ):
        parts.append((frontend / relative).read_text(encoding="utf-8"))
    return "\n".join(parts)
sys.path.insert(0, str(ROOT))

streamlit_stub = sys.modules.get("streamlit") or types.ModuleType("streamlit")

class _SessionState(dict):
    def __getattr__(self, name):
        return self.get(name)

if not hasattr(streamlit_stub, "session_state"):
    streamlit_stub.session_state = _SessionState()
streamlit_stub.error = getattr(streamlit_stub, "error", lambda *args, **kwargs: None)
streamlit_stub.exception = getattr(streamlit_stub, "exception", lambda *args, **kwargs: None)
streamlit_stub.warning = getattr(streamlit_stub, "warning", lambda *args, **kwargs: None)
components_stub = sys.modules.get("streamlit.components") or types.ModuleType("streamlit.components")
components_v1_stub = sys.modules.get("streamlit.components.v1") or types.ModuleType("streamlit.components.v1")
components_v1_stub.declare_component = getattr(components_v1_stub, "declare_component", lambda *args, **kwargs: (lambda *a, **k: None))
streamlit_stub.components = components_stub
components_stub.v1 = components_v1_stub
sys.modules["streamlit"] = streamlit_stub
sys.modules["streamlit.components"] = components_stub
sys.modules["streamlit.components.v1"] = components_v1_stub

from app_modules.itinerary_html import build_itinerary_html
from generator import group_rows_by_day
from itinerary_generation.content_validator import compact_html
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.transport import get_transport_route_phrase
from itinerary_generation.transport_times import get_transport_time_text, get_overnight_train_schedule
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.travel_sequence_blocks import _norway_nutshell_lines, get_travel_arrangement_line
from visual_editor_component.editor_workflow import build_visual_editor_payload


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_norway_in_a_nutshell_pipe_input_preserves_route_time_and_luggage():
    raw = """
Day 1	Activity	01.01.2026		Norway in a NUtshell | Oslo to Bergen | 08:35 --- 20:38 | Including luggage porter service
"""
    rows = _rows(raw)
    row = rows[0]

    assert row["title"] == "Norway in a Nutshell from Oslo to Bergen"
    assert row["time"] == "8:35 AM - 8:38 PM"
    assert "Luggage porter service" in row["includes"]
    assert get_transport_route_phrase(row) == "Norway in a Nutshell from Oslo to Bergen"

    lines = _norway_nutshell_lines(row)
    assert lines[0] == "Norway in a Nutshell from Oslo to Bergen — 8:35 AM - 8:38 PM"
    assert "Included journey: Bergen Railway, Flåm Railway, Fjord cruise, Scenic bus journey, Luggage porter service" in lines

    sections = create_categorized_inclusions(rows, group_rows_by_day(rows))
    flat = "\n".join("\n".join(section["items"]) for section in sections)
    assert "Norway in a Nutshell from Oslo to Bergen" in flat
    assert "8:35 AM - 8:38 PM" in flat
    assert "Luggage porter service" in flat


def test_santa_claus_express_extracts_departure_arrival_and_cabin_for_preview_and_inclusions():
    raw = """
Day 1	Transfer	02.01.2026	03.01.2026	Overnight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 23:04  Helsinki - Arrival 10:58  Rovaniemi  - 1  x  downstairs cabin for two people
"""
    rows = _rows(raw)
    row = rows[0]

    assert row["title"] == "Santa Claus Express to Rovaniemi"
    assert get_transport_route_phrase(row) == "Santa Claus Express to Rovaniemi"
    assert get_transport_time_text(row) == "11:04 PM - 10:58 AM"
    assert get_overnight_train_schedule(row) == {
        "departure_time": "11:04 PM",
        "departure_place": "Helsinki",
        "arrival_time": "10:58 AM",
        "arrival_place": "Rovaniemi",
    }

    line = get_travel_arrangement_line(row)
    assert "Santa Claus Express to Rovaniemi" in line
    assert "11:04 PM - 10:58 AM" in line
    assert "Departure: 11:04 PM from Helsinki" in line
    assert "Arrival: 10:58 AM in Rovaniemi" in line
    assert "1 x downstairs cabin for two people" in line

    html = build_itinerary_html(rows, group_rows_by_day(rows), {})
    plain = compact_html(html)
    assert "Santa Claus Express to Rovaniemi" in plain
    assert "11:04 PM - 10:58 AM" in plain
    assert "Departure: 11:04 PM from Helsinki" in plain
    assert "Arrival: 10:58 AM in Rovaniemi" in plain
    assert "1 x downstairs cabin for two people" in plain


def test_visual_editor_payload_and_frontend_keep_categorized_inclusion_html_visible():
    raw = """
Day 1	Hotel	01.01.2026	02.01.2026	Helsinki: Check in to your accommodation for a 1 night stay - Hotel Haven - 1 x Standard Double Room - breakfast included
Day 1	Transfer	01.01.2026		Helsinki: Private transfer to your accommodation
Day 2	Activity	02.01.2026		Norway in a NUtshell | Oslo to Bergen | 08:35 --- 20:38 | Including luggage porter service
"""
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    payload = build_visual_editor_payload(rows, grouped, {})
    pages = payload["final_pages"]["whats_included_pages_html"]

    assert pages
    joined = "\n".join(page["html"] for page in pages)
    assert "section-title" in joined
    assert "Accommodation" in joined
    assert "Scenic rail &amp; fjord journeys" in joined or "Scenic rail & fjord journeys" in joined
    assert "Norway in a Nutshell from Oslo to Bergen" in joined

    frontend = _visual_editor_frontend_source()
    assert "key.includes('.whats_included_pages_html.')" in frontend
    assert "el.innerHTML.trim()" in frontend
