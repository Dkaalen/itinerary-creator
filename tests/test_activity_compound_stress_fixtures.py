import json
from pathlib import Path

from app_modules.itinerary_html import build_itinerary_html
from generator import group_rows_by_day
from itinerary_generation.content_validator import compact_html
from itinerary_generation.day_titles import create_day_title
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.row_filters import get_row_type
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


FIXTURE_PATH = Path("tests/fixtures/quality_stress_inputs/activities_compound/activities_compound_inputs.json")


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def _plain_html(rows):
    return compact_html(build_itinerary_html(rows, group_rows_by_day(rows), {}))


def test_activity_compound_stress_fixture_bank_is_available_for_future_patches():
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert len(records) == 50
    assert {record["bank"] for record in records} == {"activities_compound"}
    assert {"umbrella_plus_detail", "detail_inside_umbrella", "nutshell", "golden_circle", "south_coast"}.issubset(
        {record["category"] for record in records}
    )


def test_tallinn_umbrella_excursion_keeps_guided_old_town_detail_row():
    raw = """
Day 1	Activity	01.01.2027		Helsinki: Excursion to Tallinn - Guided Experience - Departure from Helsinki: 10:30 am - Departure from Tallinn: 7:30 pm - Includes: ferry tickets, guided tour
Day 1	Activity	01.01.2027		Tallinn: Old Town Guided tour - Time: 1:00 pm - 3:30 pm - Meeting point: Town Hall clock - Notable sights: St Nicholas Church, Alexander Nevsky Cathedral
"""
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    plain = _plain_html(rows)

    assert create_day_title(grouped["Day 1"]) == "Day Excursion to Tallinn"
    assert "Day Excursion to Tallinn" in plain
    assert "Ferry Journey Helsinki to Tallinn return ferry" in plain
    assert "Featured experience Excursion to Tallinn - Guided Experience" not in plain
    assert "Guided Experience" not in plain
    assert "Afternoon Experience Old Town Guided Tour" in plain
    assert "Departure from Helsinki: 10:30 AM" in plain
    assert "Return from Tallinn: 7:30 PM" in plain
    assert "Meeting point: Town Hall clock" in plain
    assert "Meeting point: Town Hall clock - Notable sights" not in plain
    assert "Notable Sights St Nicholas Church Alexander Nevsky Cathedral" in plain
    assert "Explore Tallinn’s Old Town with a guide" in plain


def test_pipe_formatted_private_fjord_cruise_stays_activity_with_city_time_and_inclusions():
    rows = _rows("""
Day 1	Activity	01.01.2027		Bergen | Private Fjord Cruise | 10:00 - 14:00 | Includes guide, boat, snacks
""")
    row = rows[0]

    assert get_row_type(row) == "Activity"
    assert row["city"] == "Bergen"
    assert row["title"] == "Private Fjord Cruise"
    assert row["time"] == "10:00 AM - 2:00 PM"
    assert row["includes"] == ["guide", "boat", "snacks"]

    plain = _plain_html(rows)
    assert "Private Fjord Cruise" in plain
    assert "Time: 10:00 AM - 2:00 PM" in plain
    assert "Guide Boat Snacks" in plain

    sections = create_categorized_inclusions(rows, group_rows_by_day(rows))
    flat = "\n".join("\n".join(section["items"]) for section in sections)
    assert "Private Fjord Cruise - 1st of January" in flat
    assert "guide, boat, snacks" in flat


def test_activity_typed_leisure_row_does_not_become_fake_featured_experience():
    rows = _rows("""
Day 1	Activity	01.01.2027		Activity: Copenhagen: Spend time at leisure
""")
    row = rows[0]

    assert get_row_type(row) == "Leisure"
    assert row["city"] == "Copenhagen"
    assert create_day_title(group_rows_by_day(rows)["Day 1"]) == "A day at leisure in Copenhagen"

    plain = _plain_html(rows)
    assert "A day at leisure in Copenhagen" in plain
    assert "Featured experience Activity: Copenhagen: Spend time at leisure" not in plain
    assert "Activities & experiences" not in "\n".join(
        section["title"] for section in create_categorized_inclusions(rows, group_rows_by_day(rows))
    )


def test_golden_circle_and_south_coast_keep_stop_based_premium_descriptions():
    rows = _rows("""
Day 1	Activity	01.01.2027		Reykjavík: Golden Circle Super Jeep Tour - Time: 09:00 am - 5:00 pm - Stops: Thingvellir, Geysir, Gullfoss - Includes: guide, vehicle
Day 2	Activity	02.01.2027		Reykjavík: South Coast Adventure - Time: 08:00 am - 7:00 pm - Highlights: Seljalandsfoss, Skógafoss, Reynisfjara, Vík
""")
    plain = _plain_html(rows)

    assert "Golden Circle Super Jeep Tour" in plain
    assert "Þingvellir National Park, Geysir and Gullfoss" in plain
    assert "South Coast Adventure" in plain
    assert "Seljalandsfoss waterfall, Skógafoss and Reynisfjara" in plain
