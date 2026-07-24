from tests.support.inclusion_contract import (
    build_inclusion_sections,
    inclusion_item_text,
    inclusion_item_texts,
    inclusion_section_text,
    inclusion_text,
)
import sys
import types

streamlit_stub = sys.modules.get("streamlit") or types.ModuleType("streamlit")
streamlit_stub.session_state = getattr(streamlit_stub, "session_state", {})
streamlit_stub.warning = getattr(streamlit_stub, "warning", lambda *args, **kwargs: None)
streamlit_stub.success = getattr(streamlit_stub, "success", lambda *args, **kwargs: None)
components_stub = sys.modules.get("streamlit.components") or types.ModuleType("streamlit.components")
components_v1_stub = sys.modules.get("streamlit.components.v1") or types.ModuleType("streamlit.components.v1")
components_v1_stub.declare_component = getattr(components_v1_stub, "declare_component", lambda *args, **kwargs: (lambda **component_kwargs: None))
streamlit_stub.components = components_stub
components_stub.v1 = components_v1_stub
sys.modules["streamlit"] = streamlit_stub
sys.modules["streamlit.components"] = components_stub
sys.modules["streamlit.components.v1"] = components_v1_stub

from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from itinerary_generation.exclusion_sections import create_whats_not_included
from itinerary_generation.transport_norway import extract_norway_nutshell_route_points, format_norway_nutshell_route
from ui.travel_sequence_blocks import build_travel_arrangements_block
from visual_editor_component.editor_workflow import build_visual_editor_payload


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def _section_items(sections, title):
    for section in sections:
        if section.title == title:
            return inclusion_item_texts(section)
    return []


def test_nutshell_timetable_route_uses_premium_route_and_clean_inclusions():
    raw = """
Day 1	Transfer	02/01/2027						Oslo	"Norway in a NUtshell | Bergen to Oslo |08:30 - 22:30 | Including luggage porter service

08:29 Bergen
09:41 Voss
10:10 Voss
11:10 Gudvangen
12:00 Gudvangen
14:00 Flåm
16:50 Flåm
17:30 Myrdal
17:40 Myrdal
22:27 Oslo
"
"""
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    row = rows[0]

    points = extract_norway_nutshell_route_points(row["details"])
    assert points == ["Bergen", "Voss", "Gudvangen", "Flåm", "Myrdal", "Oslo"]
    assert format_norway_nutshell_route(points) == "Bergen, Voss, Gudvangen, Flåm, Myrdal and Oslo"

    block = build_travel_arrangements_block(grouped["Day 1"])
    html = block["html"]
    assert "Norway in a Nutshell from Bergen to Oslo" in html
    assert "Bergen → Voss → Gudvangen → Flåm → Myrdal → Oslo" in html
    assert "Route highlights:" not in html
    assert "22:30 to Oslo" not in html

    sections = build_inclusion_sections(rows, grouped)
    scenic_items = "\n".join(_section_items(sections, "Scenic rail & fjord journeys"))
    assert "Norway in a Nutshell from Bergen to Oslo" in scenic_items
    assert "Route highlights: Bergen, Voss, Gudvangen, Flåm, Myrdal and Oslo" in scenic_items
    assert "→" not in scenic_items
    assert "22:30 to Oslo" not in scenic_items


def test_santa_claus_express_uses_separate_departure_arrival_and_cabin_lines():
    raw = """
Day 1	Transfer	25/12/2026						Helsinki	Overnight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 23:04 Helsinki - Arrival 10:58 Rovaniemi - 1 x downstairs cabin for two people
"""
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    block_html = build_travel_arrangements_block(grouped["Day 1"])["html"]

    assert "Santa Claus Express to Rovaniemi" in block_html
    assert "Departure: 11:04 PM from Helsinki" in block_html
    assert "Arrival: 10:58 AM in Rovaniemi" in block_html
    assert "Cabin: 1 x downstairs cabin for two people" in block_html

    sections = build_inclusion_sections(rows, grouped)
    rail_items = "\n".join(_section_items(sections, "Rail journeys"))
    assert "Santa Claus Express to Rovaniemi" in rail_items
    assert "11:04 PM - 10:58 AM" in rail_items
    assert "Departure: 11:04 PM from Helsinki" in rail_items
    assert "Arrival: 10:58 AM in Rovaniemi" in rail_items
    assert "Cabin: 1 x downstairs cabin for two people" in rail_items
    assert "Arrival: 10:58 AM in Rovaniemi and 1 x downstairs cabin" not in rail_items


def test_floibanen_fallback_and_specific_exclusions_do_not_hide_included_activities():
    raw = """
Day 1	Activity	01/01/2027						Bergen	"Bergen: Guided Walking Tour of Bergen Past & Present |10:30 | 2 hrs
What's included?
Authorized English-speaking guide
Visit to Bergenhus Fortress
Visit Bryggen Wharf (UNESCO site)
Not included
Entrance fees to optional attractions
Transportation to meeting point
Food and drinks are excluded
What to expect?
Walk through Bergen."
Day 1	Activity	01/01/2027						Bergen	"Bergen Roundtrip Fløibanen Tickets | The Fløibanen funicular in Bergen is one of Norway’s best-known and most visited attractions. The journey up to Fløyen takes about 5–8 minutes.
Meeting Point : Vetrlidsallmenningen 23A, 5014"
"""
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    sections = build_inclusion_sections(rows, grouped)
    activities = "\n".join(_section_items(sections, "Activities & experiences"))
    exclusions = create_whats_not_included(rows)
    exclusions_text = "\n".join(exclusions)

    assert "Fløibanen Funicular - 1st of January\nRound-trip Fløibanen ticket" in activities
    assert "Guided Walking Tour of Bergen Past & Present - 1st of January" in activities
    assert "Guided Walking Tour of Bergen Past & Present - 1st of January" not in exclusions_text
    assert "Guided Walking Tour of Bergen Past & Present: Entrance fees to optional attractions, transport to the meeting point and food and drinks" in exclusions_text


def test_visual_editor_preview_gets_generated_whats_not_included_text():
    raw = """
Day 1	Transfer	29/12/2026						Tromso	Flight Rovaneimi to Tromso | self arranged cost not included
"""
    rows = _rows(raw)
    payload = build_visual_editor_payload(rows, group_rows_by_day(rows), {})
    text = payload["final_pages"]["whats_not_included_text"]

    assert "Self-arranged flights" in text
    assert "Flight from Rovaniemi to Tromsø" in text
    assert "Rovaneimi" not in text
