from __future__ import annotations

import re
from pathlib import Path

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.route_intelligence import (
    premium_mode_label,
    route_profile_for_places,
)
from itinerary_generation.transport_domain.render import build_travel_arrangements_render_block
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.render_blocks import render_block_to_html

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "activity_training" / "norway_coastal_cruise_transfer_inputs.txt"


def _fixture_input(name: str) -> str:
    text = FIXTURE.read_text(encoding="utf-8")
    parts = re.split(r"^###\s+(INPUT\s+\d+)\s*$", text, flags=re.MULTILINE)
    return {parts[index].strip(): parts[index + 1].strip() for index in range(1, len(parts), 2)}[name]


def _context(raw: str):
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    return build_itinerary_render_context(rows, grouped, {})


def test_common_nordic_route_profiles_are_available_for_core_routes():
    coastal = route_profile_for_places("Stavanger", "Bergen", "coastal_cruise", "Atlantic Coastal Cruise Transfer")
    nutshell = route_profile_for_places("Bergen", "Oslo", "norway in a nutshell")
    rail = route_profile_for_places("Kristiansand", "Stavanger", "train")

    assert coastal is not None
    assert coastal.style == "Coastal cruise transfer"
    assert "door-to-door" in coastal.intro
    assert coastal.highlights == ("Coastal sailing", "Port-to-hotel coordination", "Bergen arrival")

    assert nutshell is not None
    assert "Self-guided scenic journey" in nutshell.style
    assert "rail, coach and fjord-cruise segments" in nutshell.intro

    assert rail is not None
    assert "fjorde" not in rail.intro.lower()
    assert "fjord gateway" in rail.intro


def test_route_day_intros_use_profile_copy_instead_of_generic_transfer_language():
    context = _context(_fixture_input("INPUT 2"))
    intros = {day.day: day.intro for day in context.render_document.days}

    assert "main transfer details laid out clearly" not in "\n".join(intros.values())
    assert "Travel south from Oslo to Kristiansand" in intros["Day 2"]
    assert "Southern Norway’s coastal atmosphere" in intros["Day 2"]
    assert "Travel from Kristiansand to Stavanger by train" in intros["Day 3"]
    assert "private transfers arranged around the port departure" in intros["Day 5"]
    assert "Norway in a Nutshell route towards Oslo" in intros["Day 7"]


def test_nutshell_timeline_uses_client_facing_segment_labels():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Bergen",
            "title": "Norway in a Nutshell to Oslo",
            "details": "Bergen: Norway in a Nutshell to Oslo - Time: 08:29 am - 10:27 pm - Includes: Train transfer Bergen to Voss (08:29 am - 09:41 am), Coach transfer Voss to Gudvangen (10:10 am - 11:10 am), Fjord Cruise Gudvangen to Flåm (12:10 pm - 2:10 pm), Train transfer Flåm to Myrdal (4:00 pm - 4:57 pm), Train Transfer Myrdal to Oslo (5:40 pm - 10:27 pm)",
            "time": "08:29 am - 10:27 pm",
            "includes": [
                "Train transfer Bergen to Voss (08:29 am - 09:41 am)",
                "Coach transfer Voss to Gudvangen (10:10 am - 11:10 am)",
                "Fjord Cruise Gudvangen to Flåm (12:10 pm - 2:10 pm)",
                "Train transfer Flåm to Myrdal (4:00 pm - 4:57 pm)",
                "Train Transfer Myrdal to Oslo (5:40 pm - 10:27 pm)",
            ],
        }
    ]

    block = build_travel_arrangements_render_block(rows)
    timeline = next(section for section in block.extra_sections if section.title == "Journey timeline")

    assert timeline.items[0].startswith("Rail segment — Bergen → Voss")
    assert any(item.startswith("Coach connection — Voss → Gudvangen") for item in timeline.items)
    assert any(item.startswith("Fjord cruise — Gudvangen → Flåm") for item in timeline.items)

    html = render_block_to_html(block)["html"]
    assert "Rail segment" in html
    assert "Coach connection" in html
    assert "Fjord cruise" in html
    assert "Style:" not in html


def test_coastal_cruise_card_uses_route_profile_highlights_and_style():
    rows = [
        {
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Stavanger",
            "title": "Private transfer to Stavanger Cruise Port",
            "details": "Stavanger: Private transfer to Stavanger Cruise Port",
        },
        {
            "type": "Cruise",
            "effective_type": "Cruise",
            "city": "Stavanger",
            "title": "Atlantic Coastal Cruise Transfer to Bergen",
            "details": "Stavanger: Atlantic Coastal Cruise Transfer to Bergen - Time: 07:30 am - 1:00 pm - Meeting point: Stavanger Cruise Port - Includes: Tickets, Fjord Lounge",
            "time": "07:30 am - 1:00 pm",
            "includes": ["Tickets", "Fjord Lounge"],
        },
        {
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Bergen",
            "title": "Private transfer to your accommodation",
            "details": "Bergen: Private transfer to your accommodation",
        },
    ]

    block = build_travel_arrangements_render_block(rows)

    assert block.description == "A coordinated coastal transfer day, combining private port transfers with the scenic cruise leg to Bergen."
    assert not any(meta.label == "Style" for meta in block.meta)
    highlights = next(section for section in block.extra_sections if section.title == "Highlights")
    assert "Coastal sailing" in highlights.items

    html = render_block_to_html(block)["html"]
    assert "Coastal sailing" in html
    assert "Port-to-hotel coordination" in html
    assert "Style:" not in html


def test_premium_mode_labels_replace_raw_transport_modes():
    assert premium_mode_label("Train transfer") == "Rail segment"
    assert premium_mode_label("Coach transfer") == "Coach connection"
    assert premium_mode_label("Fjord Cruise") == "Fjord cruise"
