from scripts.real_excel_fixture_bank import build_candidate_index
from scripts.real_output_qa.rendering import render_candidate
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from generator import create_day_title, create_journey_arc, group_rows_by_day


def _fixture_candidate():
    return next(
        item
        for item in build_candidate_index()
        if item.fixture_id == "Standard-Itinerary-Finland-Norway.xlsx::1206"
    )


def _fixture_rows():
    return normalize_itinerary_rows(parse_itinerary(_fixture_candidate().raw_text))


def test_extra_day_wrapper_preserves_provenance_and_resolves_underlying_events():
    rows = [row for row in _fixture_rows() if row.get("source_type") == "Extra Day"]

    assert [(row["day"], row["type"], row["effective_type"], row["city"]) for row in rows] == [
        ("Day 8", "Flight", "Flight", "Alta"),
        ("Day 8", "Transfer", "Transfer", "Oslo"),
        ("Day 8", "Hotel", "Hotel", "Oslo"),
        ("Day 9", "Transfer", "Transfer", "Oslo"),
        ("Day 9", "Departure", "Departure", "Oslo"),
    ]
    assert all(row["source_type"] == "Extra Day" for row in rows)
    hotel = next(row for row in rows if row["effective_type"] == "Hotel")
    assert hotel["hotel_nights"] == "1"
    assert hotel["room_category"] == "Standard Room"


def test_extra_day_extension_keeps_day_title_city_and_overview_consistent():
    grouped = group_rows_by_day(_fixture_rows())

    assert create_day_title(grouped["Day 8"]) != "Departure from Oslo"
    assert create_day_title(grouped["Day 9"]) == "Departure from Oslo"
    day9_cities = {row.get("city") for row in grouped["Day 9"] if row.get("city")}
    assert day9_cities == {"Oslo"}
    final_chapter = create_journey_arc(grouped)[-1]
    assert final_chapter["chapter"] == "Oslo"
    assert final_chapter["experience"] == "Departure from Oslo"


def test_travel_day_has_one_day_level_leisure_block_owned_by_arrival_city():
    document = render_candidate(_fixture_candidate()).context.render_document
    day6 = next(day for day in document.days if int(day.number) == 6)
    leisure_blocks = [block for block in day6.blocks if block.kind == "leisure"]

    assert len(leisure_blocks) == 1
    alta_leisure = next(
        row for row in _fixture_rows()
        if row.get("day") == "Day 6" and row.get("type") == "Leisure" and row.get("city") == "Alta"
    )
    assert leisure_blocks[0].row_id == alta_leisure["row_id"]
