from __future__ import annotations

from pathlib import Path

from parser_modules.parser_main import parse_itinerary
from normalizer_modules.core import normalize_itinerary_rows
from itinerary_generation.canonical_accommodation import canonical_accommodation_block
from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.day_titles import create_day_title
from itinerary_generation.exclusion_sections import create_whats_not_included
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.transport_domain.render import get_travel_sequence_line
from text_polish import polish_title


BV_SAMPLE = """Day 1\tTransfer \t28/10/2026\t\t\t\t\tOslo\tPrivate Airport to Hotel
Day 1\tHotel\t28/10/2026\t29/10/2026\t\t\t\tOslo\t4 star ,Comfort Hotel Grand Central, 1xNight , 1x Compact  Double Room, Incl Brekafast 
Day 2\tTransfer \t29/10/2026\t\t\t\t\tOslo\tPrivate Hotel to Airport
Day 2\tTransfer \t29/10/2026\t\t\t\t\tAlta\tFlight Oslo to Alta,Self arranged 
Day 2\tTransfer \t29/10/2026\t\t\t\t\tAlta\tPrivate Airport to Hotel
Day 2\tHotel\t29/10/2026\t31/10/2026\t\t\t\tAlta\t4 Star ,Canyon Hotell , 2xNight , 1xStandard Double Room, Incl Brekafast 
Day 3\tActivity\t30/10/2026\t\t\t\t\tAlta\tAlta: Whale Watching & Arctic Wildlife Safari by RIB Boat |10:15 | 4 hrs  Pick up / meeting point
Adventure Store, Markedsgata 6, Alta

Overview
Feel the raw power of Arctic waters beneath you as your RIB boat cuts through fjord swells, bringing you eye-level with humpback whales and orcas in their winter hunting grounds.

What's included?
Pick-up/drop-off in central Alta
Knowledgeable, English-speaking guide
RIB boat trip with a certified driver
Rental of warm thermal suits
Boots, gloves, balaclava & goggles
Hot coffee, tea and snacks

Please note that while we try our best, we can not guarantee that we will actually see whales on the trip. The season start and end date can be adjusted according to whale migration patterns.
Day 4\tTransfer \t31/10/2026\t\t\t\t\tTromso\tBus , Alta to Tromso ,ticket to be bought on spot at ticket counter
Day 4\tHotel\t31/10/2026\t02/11/2026\t\t\t\tTromso\t3 Star ,Home Hotel Aurora ,,  2xNight , 1xStandard Double Room, Incl Brekafast 
Day 5\tActivity\t01/11/2026\t\t\t\t\tTromso\tTromsø: Northern Lights Safari to Aurora Basecamp | 18:15 | 7 Hrs | Pick-up/drop-off in central Tromsø , English-speaking Northern Lights guide ,Comfortable coach transport with toilet ,Northern Lights instructions video on coach ,Warm overalls and tripods at Base Station ,Snacks, drinks and soup or stew
Day 6\tTransfer \t02/11/2026\t\t\t\t\tTromso\tPrivate Hotel to Airport"""


def _rows():
    return normalize_itinerary_rows(parse_itinerary(BV_SAMPLE))


def test_bv_hotel_names_and_star_ratings_are_source_owned():
    rows = _rows()
    hotel_names = [row.get("hotel_name") for row in rows if row.get("effective_type") == "Hotel"]

    assert "Home Hotel Aurora" in hotel_names
    assert "Home Hotel Northern Lights" not in hotel_names

    aurora = next(row for row in rows if row.get("hotel_name") == "Home Hotel Aurora")
    assert aurora.get("star_rating") == "3"
    assert canonical_accommodation_block(aurora).title.startswith("3-star Home Hotel Aurora")

    inclusions = "\n".join(item for section in create_categorized_inclusions(rows) for item in section.get("items", []))
    assert "4-star Comfort Hotel Grand Central" in inclusions
    assert "4-star Canyon Hotell" in inclusions
    assert "3-star Home Hotel Aurora" in inclusions
    assert "Home Hotel Northern Lights" not in inclusions


def test_bv_bought_on_site_coach_transfer_is_excluded_with_route():
    rows = _rows()
    coach = next(row for row in rows if row.get("title") == "Coach Transfer to Tromsø")

    assert coach.get("commercial_status") == "self_arranged"
    assert create_day_title([row for row in rows if row.get("day") == "Day 4"]) == "Coach Transfer to Tromsø"
    assert get_travel_sequence_line(coach) == "Coach Transfer from Alta to Tromsø (self-arranged, not included)"

    inclusions = "\n".join(item for section in create_categorized_inclusions(rows) for item in section.get("items", []))
    assert "Coach Transfer from Alta to Tromsø" not in inclusions

    exclusions = "\n".join(create_whats_not_included(rows))
    assert "Coach Transfer from Alta to Tromsø" in exclusions
    assert "tickets to be purchased on site" in exclusions


def test_bv_final_inclusions_reuse_activity_titles():
    rows = _rows()
    aurora = next(row for row in rows if "Aurora Basecamp" in row.get("title", ""))

    assert aurora.get("title") == "Northern Lights Safari to Aurora Basecamp"
    assert create_day_title([aurora]) == "Northern Lights Safari to Aurora Basecamp"
    assert polish_title("Northern Lights Safari to Aurora Basecamp") == "Northern Lights Safari to Aurora Basecamp"

    inclusions = "\n".join(item for section in create_categorized_inclusions(rows) for item in section.get("items", []))
    assert "Northern Lights Safari to Aurora Basecamp" in inclusions
    assert "Northern Lights Safari to Northern Lights Basecamp" not in inclusions


def test_bv_whale_product_suffix_and_notes_are_preserved():
    rows = _rows()
    whale = next(row for row in rows if "Whale Watching" in row.get("title", ""))
    block = canonical_activity_block(whale)

    assert whale.get("title") == "Whale Watching & Arctic Wildlife Safari by RIB Boat"
    assert block.title == "Whale Watching & Arctic Wildlife Safari by RIB Boat"
    assert any(meta.label == "Notes" and "Whale sightings cannot be guaranteed" in meta.value for meta in block.meta)
    assert not any("guarantee" in item.lower() for item in block.includes)


def test_bv_generic_airport_transfers_resolve_to_city_airports():
    rows = _rows()
    transfer_lines = "\n".join(get_travel_sequence_line(row) for row in rows if row.get("effective_type") in {"Transfer", "Transport", "Flight"})

    assert "Private transfer from your hotel to Oslo Airport" in transfer_lines
    assert "Private transfer from your hotel to Tromsø Airport" in transfer_lines
    assert "Private transfer from your hotel to the Airport" not in transfer_lines


def test_bv_cover_preview_merge_preserves_server_image_data_uri():
    state_js = Path("visual_editor_component/frontend/js/state.js").read_text(encoding="utf-8")

    assert "serverCover[key]?.data_uri" in state_js
    assert "serverCover[key]?.auto_data_uri" in state_js
    assert "summary_image" in state_js
