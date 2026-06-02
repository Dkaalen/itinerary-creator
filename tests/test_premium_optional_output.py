from app_modules.itinerary_html import build_itinerary_html
from generator import group_rows_by_day
from itinerary_generation.day_planner import plan_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


HSDK_WALRUS_INPUT = """
Day 1	Arrival	05.08.2026		Oslo: Welcome to Norway
Day 1	Transfer	05.08.2026		Oslo: Self transfer to your accommodation
Day 1	Hotel	05.08.2026	07.08.2026	Oslo: Check in to your accommodation for a 2 night stay - Clarion Hotel The Hub - Standard Double Room - Breakfast included
Day 1	Leisure	05.08.2026		Oslo: Spend time at leisure
Day 2	Activity	06.08.2026		Oslo: Fjord Sightseeing Cruise - Time: 11:00 am - 1:00 pm - Meeting point: Rådhusbrygge 4, Platform E - Includes: Oslo Fjord archipelago cruise by electric boat, Cafeteria with snacks and drinks for purchase, "Voice of Norway" Audio guide for download, Stop at the Bygdøy peninsula near to museums - Description: Embark on a 2-hr Oslofjord Sightseeing Cruise, where history, culture, and natural beauty intertwine. As you sail, discover fortresses, lighthouses, and coastal villages that echo with centuries-old tales. Audio guides available to enhance your experience.
Day 2	Leisure	06.08.2026		Oslo: Spend time at leisure
Day 3	Transfer	07.08.2026		Oslo: Self transfer to Oslo Airport
Day 3	Flight	07.08.2026		Oslo: Flight to Svalbard - Time: 07:05 am - 10:00 am - Includes: Tickets, Luggage (1 x 23 kg check in and 1 x 8 kg carry on per person)
Day 3	Transfer	07.08.2026		Longyearbyen: Self transfer to your accommodation
Day 3	Hotel	07.08.2026	10.08.2026	Longyearbyen: Check in to your accommodation for a 3 night stay - Radisson Blu Polar Hotel, Spitsbergen - Superior Room - Breakfast included
Day 3	Leisure	07.08.2026	Longyearbyen: Spend time at leisure
Day 3	Activity	07.08.2026	Longyearbyen: Longyearbyen in a nutshell guided tour - Time: 4:00 pm - 6:00 pm - Meeting point: Hotel pick up - Includes: Local guide with extensive local knowledge - Description: A guided taxi tour around Longyearbyen offers a good dose of local knowledge, an overview of the various attractions, and, most importantly, an introduction to the general history of Svalbard.
Day 4	Activity	08.08.2026	Longyearbyen: Walrus Safari Boat Tour - Time: 09:00 am - 1:00 pm - Meeting point: Hotel pick up - Includes: Transfer to/from the harbour in Longyearbyen, Boat tour onboard Kvitbjørn, with a guide and all necessary safety equipment, Hot drinks and fresh buns from the bakery - Description: Set course on an unforgettable boat trip across Isfjorden to one of Svalbard's Walrus colonies, where we hope to see this iconic Arctic animal in its natural habitat!
Day 4	Leisure	08.08.2026	Longyearbyen: Spend time at leisure
Day 4	Activity	08.08.2026	Longyearbyen: Brewery visit at Svalbard Bryggeri - Time: 6:00 pm - 7:30 pm - Meeting point: Svalbard Bryggeri - Includes: Guided tour, beer tasting - Description: Svalbard Bryggeri is the world's northernmost brewery, located in Longyearbyen. Established in 2015, the brewery combines the pristine Arctic environment with state-of-the-art brewing techniques to create unique and high-quality beers.
Day 5	Activity	09.08.2026	Longyearbyen: Wildlife Photography Tour around Longyearbyen  - Time: 08:00 am - 1:00 pm - Meeting point: Hotel pick up - Includes: Transfer from/to accommodation in Longyearbyen, Hot drinks, biscuits and Norwegian "lefse", Loan of equipment (spikes, headlamp, snowshoes), Guide with all necessary safety equipment - Description: On this tour, we take you to the areas in and around Longyearbyen to explore and capture beautiful nature photos. The tour focuses on experiencing the wildlife and birdlife, with a special emphasis on photographing them.
Day 5	Leisure	09.08.2026	Longyearbyen: Spend time at leisure
Day 5	Optional	09.08.2026	Longyearbyen: Second Walrus Safari Boat Tour - Time: 09:00 am - 1:00 pm - Meeting point: Hotel pick up - Includes: Transfer to/from the harbour in Longyearbyen, Boat tour onboard Kvitbjørn, with a guide and all necessary safety equipment, Hot drinks and fresh buns from the bakery - Description: Set course on an unforgettable boat trip across Isfjorden to one of Svalbard's Walrus colonies, where we hope to see this iconic Arctic animal in its natural habitat!
Day 6	Transfer	10.08.2026	Longyearbyen: Self transfer to Longyearbyen Airport
Day 6	Departure	10.08.2026	Longyearbyen: Departure home via Oslo
"""


def _rows_and_grouped():
    rows = normalize_itinerary_rows(parse_itinerary(HSDK_WALRUS_INPUT))
    return rows, group_rows_by_day(rows)


def test_explicit_optional_row_renders_in_day_context_without_changing_main_day_title(monkeypatch):
    monkeypatch.setattr("ui.day_page_sections.select_day_images_with_overrides", lambda grouped_days, output_edits=None: {})
    rows, grouped = _rows_and_grouped()
    html = build_itinerary_html(rows, grouped)

    assert plan_day(grouped["Day 5"]).title == "Wildlife Photography Around Longyearbyen"
    assert "Optional Experience" in html
    assert "Second Walrus Safari Boat Tour" in html
    assert "Wildlife Photography Around Longyearbyen and Second Walrus" not in html
    assert "Included Today" not in html


def test_optional_summary_uses_client_facing_optional_experiences_style(monkeypatch):
    monkeypatch.setattr("ui.day_page_sections.select_day_images_with_overrides", lambda grouped_days, output_edits=None: {})
    rows, grouped = _rows_and_grouped()
    html = build_itinerary_html(rows, grouped)

    assert "Optional Experiences" in html
    assert "Second Walrus Safari Boat Tour - 9th of August" in html
    assert "Time: 9:00 AM - 1:00 PM" in html
    assert "Pick-up/drop-off: Hotel pick-up" in html


def test_description_label_text_beats_raw_supplier_metadata(monkeypatch):
    monkeypatch.setattr("ui.day_page_sections.select_day_images_with_overrides", lambda grouped_days, output_edits=None: {})
    rows, grouped = _rows_and_grouped()
    html = build_itinerary_html(rows, grouped)

    assert "A guided taxi tour around Longyearbyen" in html
    assert "Longyearbyen: Longyearbyen in a Nutshell" not in html
    assert "Set course on an unforgettable boat trip across Isfjorden" in html
    assert "Wildlife Photography Tour around Longyearbyen\nWildlife Photography" not in html


def test_multi_highlight_and_travel_activity_day_titles_are_client_facing():
    rows, grouped = _rows_and_grouped()

    assert plan_day(grouped["Day 3"]).title == "Journey to Svalbard and Longyearbyen Guided Tour"
    assert plan_day(grouped["Day 4"]).title == "Walrus Safari and Svalbard Brewery Visit"
