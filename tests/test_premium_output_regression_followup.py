from __future__ import annotations

import re
from pathlib import Path

from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from app_modules.itinerary_render_context import build_itinerary_render_context
from visual_editor_component.editor_payload_final_pages import build_final_pages_payload
from ui.output_edits import DEFAULT_IMPORTANT_TRAVEL_NOTES

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "activity_training" / "norway_coastal_cruise_transfer_inputs.txt"


def _fixture_input(name: str) -> str:
    text = FIXTURE.read_text(encoding="utf-8")
    parts = re.split(r"^###\s+(INPUT\s+\d+)\s*$", text, flags=re.MULTILINE)
    inputs = {parts[index].strip(): parts[index + 1].strip() for index in range(1, len(parts), 2)}
    return inputs[name]


def _context(raw: str):
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    return rows, grouped, build_itinerary_render_context(rows, grouped, {})


def test_city_specific_journey_arc_fallback_replaces_time_at_leisure():
    _rows, _grouped, context = _context(_fixture_input("INPUT 2"))
    arc = context.journey_arc

    assert arc[0]["chapter"] == "Oslo"
    assert arc[0]["experience"] == "Discover the Norwegian capital"
    assert "Time at leisure" not in [row["experience"] for row in arc]


def test_leisure_copy_is_city_specific_and_avoids_quiet_walk_filler():
    _rows, _grouped, context = _context(_fixture_input("INPUT 2"))
    leisure_blocks = [block for day in context.render_document.days for block in day.blocks if block.kind == "leisure"]
    descriptions = "\n".join(block.description for block in leisure_blocks)

    assert leisure_blocks
    assert "quiet walk nearby" not in descriptions
    assert "After arrival, keep the day gentle with time to unpack, rest, and find your bearings close to the hotel." in descriptions
    assert "Keep any spare time practical today, with room for transfers, check-in and the arranged schedule." in descriptions


def test_route_day_intros_are_not_generic_logistics_fillers():
    _rows, _grouped, context = _context(_fixture_input("INPUT 2"))
    day2 = next(day for day in context.render_document.days if day.day == "Day 2")
    day3 = next(day for day in context.render_document.days if day.day == "Day 3")
    day5 = next(day for day in context.render_document.days if day.day == "Day 5")

    all_intros = "\n".join(day.intro for day in (day2, day3, day5))
    assert "main transfer details laid out clearly" not in all_intros
    assert "Today is mainly a travel day" not in all_intros
    assert "Travel south from Oslo to Kristiansand" in day2.intro
    assert "Travel from Kristiansand to Stavanger by train" in day3.intro
    assert "coastal cruise" in day5.intro.lower()
    assert "coordinated door-to-door journey" in day5.intro


def test_special_travel_modules_render_with_native_itinerary_html():
    from itinerary_generation.transport_domain.render import build_travel_arrangements_render_block
    from ui.render_blocks import render_block_to_html

    block = build_travel_arrangements_render_block([
        {
            "type": "Cruise",
            "effective_type": "Cruise",
            "city": "Stavanger",
            "title": "Atlantic Coastal Cruise Transfer to Bergen",
            "details": "Stavanger: Atlantic Coastal Cruise Transfer to Bergen - Time: 07:30 am - 1:00 pm - Meeting point: Stavanger Cruise Port - Includes: Tickets, Fjord Lounge",
            "time": "07:30 am - 1:00 pm",
            "includes": ["Tickets", "Fjord Lounge"],
        }
    ])
    html = render_block_to_html(block)["html"]

    assert "premium-travel-card" not in html
    assert "premium-travel-timeline" not in html
    assert "content-block travel-sequence-block" in html
    assert "Journey sequence" in html
    assert "Style:" not in html


def test_visual_editor_payload_uses_premium_note_cards_for_important_notes():
    rows, grouped, context = _context(_fixture_input("INPUT 2"))
    payload = build_final_pages_payload(
        rows,
        grouped,
        {"important_travel_notes_text": "\n".join(DEFAULT_IMPORTANT_TRAVEL_NOTES)},
        {},
    )
    final_pages = payload["final_pages"]

    assert "premium-note-card" in final_pages["important_travel_notes_html"]
    assert "Transport schedules" in final_pages["important_travel_notes_html"]
