from __future__ import annotations

from itinerary_generation.canonical_accommodation import canonical_accommodation_block
from itinerary_generation.day_grouping import group_rows_by_day
from itinerary_generation.day_planner import plan_day
from itinerary_generation.content_validator import compact_html
from normalizer_modules.core import normalize_itinerary_rows
from parser_modules.parser_main import parse_itinerary
from ui.day_blocks import build_day_blocks


def _rows(raw: str) -> list[dict]:
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_stegastein_electric_minibus_is_sightseeing_activity_not_transfer():
    raw = '''Day 3\tActivity\t\t25/10/2026\t\t\t\t\t\tFlam\t"Electric minibus to Stegastein and return
Experience the stunning Stegastein viewpoint on this guided sightseeing tour from Flåm with an electric bus. The Electric Minibus to Stegastein Viewpoint is a fun, thrilling and totally green activity."'''

    rows = _rows(raw)
    activity = rows[0]
    grouped = group_rows_by_day(rows)
    day_html = compact_html("\n".join(block["html"] for block in build_day_blocks(grouped["Day 3"]) if block))

    assert activity["effective_type"] == "Activity"
    assert activity["title"] == "Electric Minibus to Stegastein Viewpoint"
    assert activity.get("activity_product", {}).get("canonical_family") == "flam_stegastein_electric_minibus"
    assert "Coach Transfer to Stegastein" not in day_html
    assert "Electric Minibus to Stegastein Viewpoint" in day_html


def test_multi_leg_train_and_self_arranged_flight_titles_day_by_final_destination():
    raw = '''Day 6\tTransfer \t\t28/10/2026\t\t\t\t\t\tOslo\tTrain : bergen to Oslo , Sitting coach
Day 6\tTransfer \t\t28/10/2026\t\t\t\t\t\tHelsinki \tFlgiht to helsinki, self arrange , cost not included
Day 6\tHotel\t\t28/10/2026\t29/10/2026\t\t\t\t\tHelsinki \t3 Star Hotel arthur , 1xNight , 1xStandard Double Room, Incl Brekafast '''

    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    plan = plan_day(grouped["Day 6"])
    flight = next(row for row in rows if row["effective_type"] == "Flight")

    assert plan.title == "Travel to Helsinki"
    assert flight["title"] == "Flight to Helsinki"
    assert flight["commercial_status"] == "self_arranged"
    assert "Flgiht" not in f"{flight['title']} {flight['details']} {flight['original_title']}"


def test_activity_column_transfer_to_igloo_becomes_accommodation_led_stay_day():
    raw = '''Day 10\tActivity\t\t01/11/2026\t\t\t\t\t\tRovaniemi\tTrasnfer to Igloo stay
Day 10\tHotel\t\t01/11/2026\t02/11/2026\t\t\t\t\tRovaniemi\t4 Star , Santa's Igloos Arctic Circle , 1xnight ,Premium double igloo , Incl brekafast '''

    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    plan = plan_day(grouped["Day 10"])
    transfer = next(row for row in rows if row["effective_type"] == "Transfer")
    hotel = next(row for row in rows if row["effective_type"] == "Hotel")
    block = canonical_accommodation_block(hotel)

    assert transfer["title"] == "Transfer to Igloo stay"
    assert plan.title == "Santa's Igloos Arctic Circle Stay"
    assert hotel["room_category"] == "Premium Double Igloo"
    assert block.lines == ["Room category: Premium Double Igloo, breakfast included"]
    assert "Trasnfer" not in f"{transfer['title']} {transfer['details']} {transfer['original_title']}"


def test_room_category_aurora_nest_is_preserved_in_day_page_accommodation_block():
    raw = '''Day 6\tTransfer \t19/12/2026\t\t\t\t\t\t\tRovaniemi\tPrivate Transfer to Glass Igloo Stay
Day 6\tHotel\t19/12/2026\t20/12/2026\t\t\t\t\t\tRovaniemi\tAito Igloo & Spa Resort , 1xngiht , 2xAurora Nest ( Similar to Igloo ) , incl breakfast'''

    rows = _rows(raw)
    hotel = next(row for row in rows if row["effective_type"] == "Hotel")
    block = canonical_accommodation_block(hotel)

    assert "Aurora Nest" in hotel["room_category"]
    assert "Northern Lights Nest" not in hotel["room_category"]
    assert any("Aurora Nest" in line for line in block.lines)
    assert not any("Northern Lights Nest" in line for line in block.lines)


def test_reindeer_inclusion_typo_is_cleaned():
    raw = '''Day 8\tActivity\t21/12/2026\t\t\t\t\t\tTromso\t"Tromsø: Reindeer Sledding, Feeding and Sami Culture | 10 AM | 5 Hrs | What's included?
Entrance to the fence and feeding the her
Reindeer Sledding for 30 minutes approx.
Hot drinks & hot meal (Sámi stew or veg option)"'''

    rows = _rows(raw)
    activity = next(row for row in rows if row["effective_type"] == "Activity")

    assert any("feeding the herd" in item.lower() for item in activity["includes"])
    assert not any(item.lower().strip() == "entrance to the fence and feeding the her" for item in activity["includes"])


def test_structured_travel_sequence_owns_multi_leg_final_destination_before_rendering():
    from itinerary_generation.structured_builder import build_itinerary_document
    from itinerary_generation.day_render_blocks import build_render_day_from_document

    raw = '''Day 6	Transfer 		28/10/2026						Oslo	Train : bergen to Oslo , Sitting coach
Day 6	Transfer 		28/10/2026						Helsinki 	Flgiht to helsinki, self arrange , cost not included
Day 6	Hotel		28/10/2026	29/10/2026					Helsinki 	3 Star Hotel arthur , 1xNight , 1xStandard Double Room, Incl Brekafast '''

    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    document = build_itinerary_document(rows, grouped)
    sequences = [sequence for sequence in document.travel_sequences if sequence.day == "Day 6"]

    assert len(sequences) == 1
    assert sequences[0].final_destination == "Helsinki"
    assert sequences[0].primary_travel_mode == "Flight"
    assert sequences[0].self_arranged is True
    assert len(sequences[0].legs) == 2

    render_day = build_render_day_from_document(document, "Day 6", grouped["Day 6"])
    travel_blocks = [block for block in render_day.blocks if block.kind == "travel_sequence"]

    assert len(travel_blocks) == 1
    assert travel_blocks[0].row_id == sequences[0].sequence_id
    assert list(sequences[0].source_row_ids) == travel_blocks[0].source_row_ids


def test_cruise_leisure_rows_stay_out_of_structured_travel_sequence():
    from itinerary_generation.structured_builder import build_itinerary_document
    from itinerary_generation.day_render_blocks import build_render_day_from_document

    raw = '''Day 9\tCruise\t\t09/10/2026\t\t\t\t\t\tCruise\tCoastal Cruise onboard the cruise Cruise: Spend time at leisure'''

    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    document = build_itinerary_document(rows, grouped)

    assert not document.travel_sequences

    render_day = build_render_day_from_document(document, "Day 9", grouped["Day 9"])
    assert not [block for block in render_day.blocks if block.kind == "travel_sequence"]
    assert any(block.kind == "cruise_leisure" for block in render_day.blocks)
    assert any(block.title == "Spend time at leisure onboard the cruise" for block in render_day.blocks)
