from __future__ import annotations

from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.parse_workflow import parse_and_normalize_itinerary
from images.matcher_context import build_day_context
from images.matcher_selection import select_best_candidate_for_context
from images.scanner import get_image_bank_index
from itinerary_generation.common import get_row_type, group_rows_by_day
from itinerary_generation.transport import get_primary_transport_title, get_transport_route_phrase


FINLAND_MESSY_INPUT = r'''Day 1	Transfer 		01/10/2026					Helsinki 	Private Airport to Hotel
Day 1	Hotel		01/10/2026	02/10/2026				Helsinki 	"4Star, Scandic Simonkenttä , 1xNight , 2xFamily Triple Room (Standard) , 2 Twin Beds and 1 Twin Sofa Bed
, Incl Brekafast "
Day 2	Activity		02/10/2026					Helsinki 	"A Finntastic Walking Tour in Helsinki | 10:30  AM | 2.15 Hr | Professional authorised Helsinki Guide 

Meeting Point : Senate Square "
Day 2	Transfer 		02/10/2026					Helsinki 	Self transfer  Hotel to Station, dist 350 metre , walking distance 
Day 2	Transfer 		02/10/2026					Helsinki 	Overnight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 11:13 pm - 10:59 am - 3  x  downstairs cabin for two people
Day 3	Transfer 		03/10/2026					Rovaniemi	Private Station to Hotel
Day 3	Hotel		03/10/2026	06/10/2026				Rovaniemi	"3 Star, Arctic city hotel  , 2xNight , 2 x Style Twin Room 

2x Single Bed, 1x Single Sofa Bed Incl Brekafast 

access to Hotel sauna "
Day 3	Activity		03/10/2026					Rovaniemi	"""""""Rovaniemi: Northern Lights Hunt with Lappish BBQ |20:00 | 3 hrs  

Pick up / meeting point :  Travels Office, Maakuntakatu 29, Rovaniem

Overview
Hunt for the Northern Lights in the middle of the untouched nature, escaping from the light pollution of the town. Taste a traditional Lappish barbecue and warm yourself by the fire while waiting for the magical lights.

What's included?
Knowledgeable, English-speaking guide
Pick-up/drop-off in central Rovaniemi
Winter clothes (overalls and boots)
Campfire BBQ with soup and sausages

Departure: Anytime between 18:00 - 22:00

Duration: 3 hours
"""
Day 4	Activity		04/10/2026					Rovaniemi	"""Rovaniemi: Santa Claus Village Visit the Magic of Christmas | 10:30 | 2 hrs 

Pick up / meeting point : Adventures Office, Koskikatu 24, Rovaniemi

Overview
Santa Claus Village Visit

What's included?
Pick-up/drop-off in central Rovaniemi
Round-trip car transportation
Short guided introduction
Self-guided experience

Not included 

Winter clothing and gear
Activity tickets and entry fees
Meals and refreshments

What to expect?
Welcome to discover the magic of Christmas in Lapland!

This visit takes you straight to the official home of Santa Claus, where you can meet Santa, send greetings from Santa’s Post Office and experience the unforgettable moment of crossing the Arctic Circle!

Recommendations and Top Activities in the Village (Please note that the journey to Santa Claus Village is independent and does not include a guide for the whole duration of the tour. You are free to enjoy your time and choose activities at your own pace.) 

Winter Activities: Enjoy a variety of winter activities, husky or reindeer- sledding (note that these activities are not included in the price)."""
Day 5	Activity		05/10/2026					Rovaniemi	Leisure Day 
Day 6	Transfer 		06/10/2026					Rovaniemi	Private Hotel to Bus station 
Day 6	Transfer 		06/10/2026					Kakslauttenen	"Bus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Kakslauttenen Arctic Resort - 11:45 am - 3:02 pm - Tickets Included

Booking window not yet opened, final ti ming can be changed/updated . final timing to be given in booking voucher "
Day 6	Hotel		06/10/2026	07/10/2026				Kakslauttenen	4 star , Kakslauttenen Arctic Resort ,2xSmall Glass Igloo with Shower and Sauna (East village) , incl breakfast+dinner
Day 7	Transfer 		07/10/2026					Rovaniemi	Shuttle Transfer  Kakslauttenen to Ivalo Airport
'''


def _rows():
    return parse_and_normalize_itinerary(FINLAND_MESSY_INPUT)


def _context():
    rows = _rows()
    return rows, build_itinerary_render_context(
        rows,
        group_rows_by_day(rows),
        {"output_brand": "booknordics_customer", "color_preset": "Booknordics B2C"},
    )


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


def test_leisure_day_activity_row_becomes_free_time_not_included_activity():
    rows, context = _context()
    leisure_row = next(row for row in rows if str(row.get("details") or row.get("title") or "").strip() == "Leisure Day")
    activity_labels = [item.label for section in context.categorized_inclusions if section.title == "Activities & experiences" for item in section.items]

    assert get_row_type(leisure_row) == "Leisure"
    assert _day(context, "5").title == "A day at leisure in Rovaniemi"
    assert "Leisure Day" not in activity_labels
    assert "Featured experience" not in _all_day_text(_day(context, "5"))


def test_santa_village_optional_husky_reindeer_text_does_not_become_included_product():
    _, context = _context()
    day4 = _day(context, "4")
    day4_text = _all_day_text(day4)
    activity_labels = [item.label for section in context.categorized_inclusions if section.title == "Activities & experiences" for item in section.items]
    exclusion_labels = [item.label for section in context.structured_whats_not_included for item in section.items]

    assert day4.title == "Santa Claus Village Visit"
    assert "Husky" not in day4.title
    assert "Reindeer" not in day4.title
    assert "husky and reindeer encounters" not in day4_text.lower()
    assert "Santa’s Post Office" in day4_text
    assert "Arctic Circle" in day4_text
    assert "Santa Claus Village Visit - 4th of October" in activity_labels
    assert any("Santa Claus Village Visit:" in label and "activity tickets" in label for label in exclusion_labels)


def test_northern_lights_lappish_bbq_uses_source_evidence_not_generic_fjord_photo_copy():
    _, context = _context()
    day3_text = _all_day_text(_day(context, "3"))

    assert "campfire barbecue" in day3_text.lower()
    assert "local guidance" in day3_text
    assert "photo-focused" not in day3_text.lower()
    assert "fjords and coastal scenery" not in day3_text.lower()


def test_final_transfer_sets_endpoint_title_intro_and_inclusions():
    rows, context = _context()
    day7 = _day(context, "7")
    transfer_row = next(row for row in rows if row.get("day") == "Day 7")
    other_transport_labels = [item.label for section in context.categorized_inclusions if section.title == "Other arranged transport" for item in section.items]

    assert context.trip_glance["End"] == "Ivalo"
    assert day7.title == "Transfer to Ivalo Airport"
    assert day7.intro == "After check-out, take your arranged transfer from Kakslauttanen to Ivalo Airport for your onward journey."
    assert "Shuttle transfer from Kakslauttanen to Ivalo Airport" in _all_day_text(day7)
    assert get_primary_transport_title([transfer_row]) == "Transfer to Ivalo Airport"
    assert get_transport_route_phrase(transfer_row) == "Shuttle transfer from Kakslauttanen to Ivalo Airport"
    assert "Shuttle transfer from Kakslauttanen to Ivalo Airport" in other_transport_labels


def test_hotel_bed_counts_amenities_and_night_mismatch_are_preserved():
    rows, context = _context()
    helsinki_hotel = next(row for row in rows if row.get("hotel_name") == "Scandic Simonkenttä")
    rovaniemi_hotel = next(row for row in rows if row.get("hotel_name") == "Arctic city hotel")
    day3_text = _all_day_text(_day(context, "3"))
    inclusion_text = "\n".join("\n".join(item.detail_lines) for section in context.categorized_inclusions for item in section.items)

    assert helsinki_hotel["room_category"] == "2 x Family Triple Room (Standard) - 2 x twin beds and 1 x single sofa bed"
    assert rovaniemi_hotel["room_category"] == "2 x Style Twin Room - 2 x single beds and 1 x single sofa bed"
    assert rovaniemi_hotel["hotel_night_mismatch"] == "source=2; dates=3"
    assert rovaniemi_hotel["hotel_amenities"] == ["Access to the hotel sauna"]
    assert "Access to the hotel sauna" in day3_text
    assert "Access to the hotel sauna" in inclusion_text


def test_overnight_lapland_train_context_prefers_winter_default_image_over_summer_track():
    rows = _rows()
    grouped = group_rows_by_day(rows)
    context = build_day_context("Day 2", grouped["Day 2"])
    index = get_image_bank_index()
    selected = select_best_candidate_for_context("Day 2", context, list(index.candidates_for_context(context)))

    assert selected is not None
    assert "Winter" in selected["filename"] or "Northern_Lights" in selected["filename"]
    assert "Summer_Train" not in selected["filename"]
