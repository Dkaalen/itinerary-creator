from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.accommodation_brain import accommodation_brain_for_row, normalize_star_rating
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_leisure_writer import write_leisure_copy
from itinerary_generation.schedule_brain import build_day_schedule_profile
from shared.source_text_cleanup import clean_supplier_text, clean_supplier_time, clean_supplier_title
from itinerary_generation.title_brain import write_day_title
from itinerary_parser import parse_itinerary

FIXTURE = Path(__file__).resolve().parent / "fixtures/real_inputs/norway_sub_brain_sample.txt"


@lru_cache(maxsize=1)
def _grouped():
    rows = parse_itinerary(FIXTURE.read_text(encoding="utf-8"))
    return rows, group_rows_by_day(rows)


@lru_cache(maxsize=1)
def _context():
    rows, grouped = _grouped()
    return build_itinerary_render_context(rows, grouped, {"output_brand": "booknordics_customer"})


def test_accommodation_brain_preserves_source_star_range():
    rows, grouped = _grouped()
    hotel = next(row for row in grouped["Day 1"] if row["type"] == "Hotel")
    brain = accommodation_brain_for_row(hotel)

    assert normalize_star_rating("", source_text=hotel["details"]) == "3/4"
    assert brain.star_rating == "3/4"
    assert "3/4-star hotel" in brain.title
    assert not re.search(r"(?<!3/)4-star hotel", brain.title)


def test_schedule_brain_blocks_false_rest_of_day_open_copy():
    _rows, grouped = _grouped()
    facts = build_day_facts(grouped["Day 5"])
    schedule = build_day_schedule_profile(grouped["Day 5"])
    leisure = write_leisure_copy(facts, classify_day_intent(facts))

    assert schedule.has_multiple_arranged_activities is True
    assert schedule.has_activity_after_leisure is True
    assert "gap between the included experiences" in leisure
    assert "rest of the day is open" not in leisure.lower()


def test_title_brain_represents_whole_mixed_days():
    _rows, grouped = _grouped()

    assert write_day_title(grouped["Day 3"]) == "Bergen Walking Tour & Fløibanen"
    assert write_day_title(grouped["Day 4"]) == "Arrival in Tromsø & Northern Lights Cruise"
    assert write_day_title(grouped["Day 5"]) == "Reindeer & Sámi Culture and Northern Lights Hunt"


def test_supplier_cleanup_brain_repairs_common_supplier_noise():
    assert clean_supplier_time("Date dependant") == "Time to be confirmed"
    assert clean_supplier_text("Free wifi") == "Free Wi-Fi"
    assert clean_supplier_title("All-Evening Northern Lights Hunt by Minibus or bus") == "All-Evening Northern Lights Hunt by Minibus or Bus"
    assert clean_supplier_text("Knowledgeable English and Norwegian speaking guide") == "Knowledgeable English- and Norwegian-speaking guide"


def test_trip_brain_avoids_western_norway_when_route_includes_tromso():
    context = _context()

    assert context.trip_title == "Norway Winter Highlights"
    assert "Western Norway" not in context.trip_title
    assert "Arctic experiences" in context.trip_subtitle


def test_render_context_uses_all_sub_brain_outputs():
    context = _context()
    by_day = {day.day: day for day in context.render_document.days}

    assert by_day["Day 1"].blocks[1].title.startswith("Centrally located 3/4-star hotel")
    assert by_day["Day 4"].title == "Arrival in Tromsø & Northern Lights Cruise"
    assert by_day["Day 5"].title == "Reindeer & Sámi Culture and Northern Lights Hunt"
    assert "Minibus or Bus" in by_day["Day 5"].intro
    assert "rest of the day is open" not in " ".join(block.description for block in by_day["Day 5"].blocks).lower()
