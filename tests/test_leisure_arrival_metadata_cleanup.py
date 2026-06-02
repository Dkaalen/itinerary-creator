import json
from pathlib import Path

from generator import group_rows_by_day
from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.day_titles import create_day_title
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.row_filters import get_row_type
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.simple_day_blocks import build_departure_block


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_leisure_arrival_departure_fixture_bank_is_available_for_future_patches():
    path = Path("tests/fixtures/quality_stress_inputs/leisure_arrival_departure/leisure_arrival_departure_inputs.json")
    records = json.loads(path.read_text(encoding="utf-8"))

    assert len(records) == 50
    assert {record["bank"] for record in records} == {"leisure_arrival_departure"}
    assert {"activity_typed_leisure", "arrival", "departure", "mixed_travel_leisure"}.issubset(
        {record["category"] for record in records}
    )


def test_metadata_content_cleanup_fixture_bank_is_available_for_future_patches():
    path = Path("tests/fixtures/quality_stress_inputs/metadata_content_cleanup/metadata_content_cleanup_inputs.json")
    records = json.loads(path.read_text(encoding="utf-8"))

    assert len(records) == 50
    assert {record["bank"] for record in records} == {"metadata_content_cleanup"}
    assert {"inline_description", "highlights", "pipe_metadata", "supplier_cta"}.issubset(
        {record["category"] for record in records}
    )


def test_activity_typed_independent_leisure_row_stays_free_time_not_fake_activity():
    rows = _rows("""
Day 1	Activity	01.01.2027		Bergen: Morning at leisure and optional self-guided walk around Bryggen
""")
    row = rows[0]

    assert get_row_type(row) == "Leisure"
    assert row["title"] == "Spend time at leisure"
    assert create_day_title(group_rows_by_day(rows)["Day 1"]) == "A day at leisure in Bergen"
    assert "Activities & experiences" not in "\n".join(
        section["title"] for section in create_categorized_inclusions(rows, group_rows_by_day(rows))
    )


def test_arranged_activity_with_leisure_wording_stays_real_activity():
    rows = _rows("""
Day 1	Activity	01.01.2027		Oslo: Free time at leisure before Munch Museum Visit - Time: 2:00 pm - 4:00 pm - Includes: Museum ticket
""")
    row = rows[0]

    assert get_row_type(row) == "Activity"
    assert row["title"] == "Munch Museum Visit"
    assert row["time"] == "2:00 PM - 4:00 PM"
    assert row["includes"] == ["Museum ticket"]


def test_inline_metadata_labels_do_not_leak_into_activity_title_description_or_sights():
    rows = _rows("""
Day 1	Activity	01.01.2027		Oslo: Private City Walk - Highlights: Royal Palace, Akershus Fortress - Includes: Guide, Coffee - Description: Explore central Oslo with your local guide. Includes: Internal supplier note. Excludes: Lunch
""")
    row = rows[0]
    block = canonical_activity_block(row)

    assert row["title"] == "Private City Walk"
    assert block.title == "Private City Walk"
    assert block.description == "Explore central Oslo with your local guide."
    assert block.includes == ["Guide", "Coffee"]
    assert block.notable_sights == ["Royal Palace", "Akershus Fortress"]
    visible = "\n".join([block.title, block.description, "\n".join(block.includes), "\n".join(block.notable_sights)])
    assert "Highlights:" not in visible
    assert "Includes:" not in visible
    assert "Excludes:" not in visible
    assert "Internal supplier note" not in visible


def test_departure_block_rejects_raw_checkout_airport_logistics_as_title():
    block = build_departure_block(
        {
            "row_id": "dep1",
            "city": "Oslo",
            "title": "Check out and transfer to the airport for your return flight home",
        }
    )

    assert "Journey home" in block["html"]
    assert "Check out and transfer" not in block["html"]
