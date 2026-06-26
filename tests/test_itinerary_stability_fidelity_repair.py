from __future__ import annotations

from parser_modules.parser_main import parse_itinerary
from itinerary_generation.common import get_row_type, group_rows_by_day
from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.titles import create_client_activity_title
from itinerary_generation.transport_domain.titles import get_transport_route_phrase


KRISTIANSAND_SCENIC_INPUT = """Day 1\tArrival\t03.09.2026\t\tKristiansand: Welcome to Norway
Day 1\tTransfer\t03.09.2026\t\tKristiansand: Self transfer to your accommodation
Day 1\tHotel\t03.09.2026\t06.09.2026\tKristiansand: Check in to your accommodation for a 2 night stay - Self arranged
Day 1\tLeisure\t03.09.2026\t\tKristiansand: Spend time at leisure
\t\t\t\t
Day 2\tLeisure\t04.09.2026\t\tKristiansand: Spend time at leisure
\t\t\t\t
Day 3\tLeisure\t05.09.2026\t\tKristiansand: Spend time at leisure
Day 3\tTransfer\t05.09.2026\t\tKristiansand: Self transfer to Kristiansand Cruise Port 
Day 3\tCruise\t05.09.2026\t\tKristiansand: Overnight Coastal Cruise to Bergen - Time: 11:15 pm - 1:00 pm - Includes: Standard Sleeper cabin, breakfast included 
\t\t\t\t
Day 4\tTransfer\t06.09.2026\t\tBergen: Self transfer to your accommodation
Day 4\tHotel\t06.09.2026\t07.09.2026\tBergen: Check in to your accommodation for a 1 night stay - Comfort Hotel Bergen - Standard Double room - Breakfast included
Day 4\tActivity\t06.09.2026\t\tBergen: Fløibanen Funicluar - Time: Flexible - Meeting point: Vetrlidsallmenningen 23A - Includes: Tickets - Description: Take the funicular Fløibanen to the top of Mount Fløyen and experience spectacular views of the city, the fjord and the surrounding mountains.
\t\t\t\t
Day 5\tTransfer\t07.09.2026\t\tBergen: Self transfer to Bergen Train Station
Day 5\tTrain\t07.09.2026\t\tBergen: Scenic Train Transfer to Voss - Time: 11:49 am - 12:58 pm - Includes: Tickets
Day 5\tTransfer\t07.09.2026\t\tVoss: Self transfer to your accommodation
Day 5\tHotel\t07.09.2026\t08.09.2026\tVoss: Check in to your accommodation for a 1 night stay - Scandic Voss - Standard Double room - Breakfast included
Day 5\tLeisure\t07.09.2026\t\tVoss: Spend time at leisure
\t\t\t\t
Day 6\tTransfer\t08.09.2026\t\tVoss: Self transfer to Voss Station
Day 6\tCoach\t08.09.2026\t\tVoss: Scenic Coach Transfer to Gudvangen - Time: 09:50 am - 10:55 am - Includes: Tickets
Day 6\tLeisure\t08.09.2026\t\tGudvangen: Spend time at leisure
Day 6\tCruise\t08.09.2026\t\tGudvangen: Nærøyfjord Cruise to Flåm - Time: 12:00 pm - 2:00 pm - Includes: Tickets
Day 6\tTransfer\t08.09.2026\t\tFlåm: Self transfer to your accommodation
Day 6\tHotel\t08.09.2026\t10.09.2026\tFlåm: Check in to your accommodation for a 2 night stay - Fretheim Hotel - America Wing Double room - Breakfast included
Day 6\tLeisure\t08.09.2026\t\tFlåm: Spend time at leisure
\t\t\t\t
Day 7\tActivity\t09.09.2026\t\tFlåm: Tour to Borgund Stave Church and Stegastein viewpoint - Time: 1:30 pm - 5:30 pm - Meeting point: Flåm centre at ordinary bus stops A and B -  Includes: Transport by electric minibus, entrance ticket to Borgund stave church, Audio guide in English, Stegastein viewpoint - Description: The tour starts near the railway station in Flåm and continues out the beautiful bay towards Aurland. On the way to Borgund, the bus will take you through the 24,5 km long Lærdalstunnel, which is the world's longest road tunnel.
Day 7\tLeisure\t09.09.2026\t\tFlåm: Spend time at leisure
\t\t\t\t
Day 8\tTransfer\t10.09.2026\t\tFlåm: Self transfer to Flåm Station
Day 8\tTrain\t10.09.2026\t\tFlåm: Flåmsbanen Train Transfer to Myrdal - Time: 12:10 pm - 1:08 pm - Includes: Tickets
Day 8\tTrain\t10.09.2026\t\tMyrdal: Train transfer to Bergen - Time: 1:13 pm - 3:24 pm - Includes: Tickets
Day 8\tTransfer\t10.09.2026\t\tBergen: Self transfer to your accommodation
Day 8\tHotel\t10.09.2026\t12.09.2026\tBergen: Check in to your accommodation for a 2 night stay - Comfort Hotel Bergen - Standard Double room - Breakfast included
Day 8\tLeisure\t10.09.2026\t\tBergen: Spend time at leisure
\t\t\t\t
Day 9\tActivity\t11.09.2026\t\tBergen: 2h Bergen Must-See Tour on Foot & by Boat - Time: 1:00 pm - 3:00 pm - Meeting point: Strandkaien 3 - Includes: Authorized, English-speaker guide, Guided walking tour of Bergen, City cruise with panoramic views, Visit to Bergen Bryggen UNESCO area, Visit to Bergen Fish Market, Visit to St. Mary's Church - Description: This 2-in-1 tour offers the ultimate Bergen experience, combining history, culture, and fjord exploration. Stroll through the alleys of the old timber town, hear fascinating stories about the city and its people, and discover centuries of history.
Day 9\tLeisure\t11.09.2026\t\tBergen: Spend time at leisure
\t\t\t\t
Day 10\tTransfer\t12.09.2026\t\tBergen: Self transfer to Bergen Airport
Day 10\tDeparture\t12.09.2026\t\tBergen: Departure home
"""


def _context(output_edits=None):
    rows = parse_itinerary(KRISTIANSAND_SCENIC_INPUT)
    return rows, build_itinerary_render_context(rows, group_rows_by_day(rows), output_edits or {"output_brand": "booknordics_customer"})


def _day(context, number: str):
    return next(day for day in context.render_document.days if day.number == number)


def _all_day_text(day) -> str:
    pieces = [day.title, day.intro]
    for block in day.blocks:
        pieces.extend([block.section_title, block.title, block.description])
        pieces.extend(block.lines)
        pieces.extend(block.includes)
        for section in block.extra_sections:
            pieces.append(section.title)
            pieces.extend(section.items)
    return "\n".join(str(piece) for piece in pieces if piece)


def test_day_pages_export_in_canonical_day_order_even_after_editor_reorder():
    rows = parse_itinerary(KRISTIANSAND_SCENIC_INPUT)
    dirty_editor_order = {
        "output_brand": "booknordics_customer",
        "editor_draft": {
            "document_pages": [
                {"page_id": "day-day-1", "sort_order": 1},
                {"page_id": "day-day-3", "sort_order": 2},
                {"page_id": "day-day-4", "sort_order": 3},
                {"page_id": "day-day-2", "sort_order": 4},
            ]
        },
    }
    context = build_itinerary_render_context(rows, group_rows_by_day(rows), dirty_editor_order)

    day_pages = [page_id for page_id in context.render_document.page_order if page_id.startswith("day-day-")]

    assert day_pages[:4] == ["day-day-1", "day-day-2", "day-day-3", "day-day-4"]


def test_self_arranged_accommodation_is_excluded_without_artifacts():
    rows, context = _context()
    kristiansand_hotel = next(row for row in rows if get_row_type(row) == "Hotel" and row.get("city") == "Kristiansand")

    assert kristiansand_hotel["hotel_nights"] == "2"
    assert kristiansand_hotel["hotel_night_mismatch"] == "source=2; dates=3"
    assert _all_day_text(_day(context, "1")).count("Self-arranged accommodation in Kristiansand for 2 nights") == 1

    included_text = "\n".join(item.label for section in context.categorized_inclusions for item in section.items)
    exclusion_text = "\n".join(
        [section.title for section in context.structured_whats_not_included]
        + [item.label for section in context.structured_whats_not_included for item in section.items]
    )

    assert "Self-arranged accommodation in Kristiansand" not in included_text
    assert "Self-arranged accommodation in Kristiansand for 2 nights" in exclusion_text
    assert "Activity-specific exclusions" not in exclusion_text
    assert "self-arranged - 3rd of September" not in exclusion_text
    assert "\naccommodation\n" not in exclusion_text.lower()


def test_scenic_western_norway_is_not_rebranded_as_nutshell_and_keeps_route_fidelity():
    rows, context = _context()
    document_text = "\n".join(_all_day_text(day) for day in context.render_document.days)
    journey_arc_text = "\n".join(item["experience"] for item in context.journey_arc)
    inclusion_text = "\n".join(item.label for section in context.categorized_inclusions for item in section.items)

    day3_text = _all_day_text(_day(context, "3"))
    day4_text = _all_day_text(_day(context, "4"))
    day6_text = _all_day_text(_day(context, "6"))

    assert "Norway in a Nutshell" not in document_text
    assert "Norway in a Nutshell" not in journey_arc_text
    assert "Scenic rail to Voss" in journey_arc_text
    assert "Nærøyfjord, Stave Church and Stegastein" in journey_arc_text
    assert "Norway in a Nutshell" not in inclusion_text
    assert "Self-arranged transfer to Kristiansand Cruise Port" in day3_text
    assert "private port transfers" not in day3_text.lower()
    assert "Cruise arrival to Bergen Port" in day4_text
    assert _day(context, "6").title == "Journey to Flåm via Gudvangen"
    assert "Nærøyfjord Cruise from Gudvangen to Flåm" in day6_text
    assert "Nærøyfjord Cruise from Nærøyfjord Cruise to Flåm" not in day6_text
    assert "Nærøyfjord Cruise from Gudvangen to Flåm" in inclusion_text

    cruise_row = next(row for row in rows if get_row_type(row) == "Cruise" and row.get("city") == "Gudvangen")
    assert get_transport_route_phrase(cruise_row) == "Nærøyfjord Cruise from Gudvangen to Flåm"


def test_activity_titles_and_inclusions_preserve_source_evidence():
    rows, context = _context()
    day7 = _day(context, "7")
    day9_text = _all_day_text(_day(context, "9"))
    activity_row = next(row for row in rows if get_row_type(row) == "Activity" and row.get("city") == "Flåm")

    assert day7.title == "Borgund Stave Church & Stegastein Viewpoint Tour"
    assert create_client_activity_title(activity_row) == "Borgund Stave Church & Stegastein Viewpoint Tour"
    assert "City cruise with panoramic views" in day9_text


def test_travel_notes_are_context_aware_for_september_western_norway():
    _, context = _context()
    notes_text = "\n".join(context.important_travel_notes)

    assert "Northern Lights" not in notes_text
    assert "Route, road and rail conditions in the Nordic region can vary in winter" not in notes_text
    assert "Some transfers are self-arranged unless specifically listed as included" in notes_text
    assert "especially during winter conditions" not in notes_text
