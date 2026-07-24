from tests.support.inclusion_contract import (
    build_inclusion_sections,
    inclusion_item_text,
    inclusion_item_texts,
    inclusion_section_text,
    inclusion_text,
)
from generator import create_journey_arc, group_rows_by_day
from itinerary_generation.content_validator import compact_html
from itinerary_generation.transport_norway import extract_norway_nutshell_route_legs, extract_norway_nutshell_route_points
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.day_blocks import build_day_blocks


QG_C_INPUT = """
	Day 4	Arrival	26/12/2026							Rovaniemi	Private Station to Hotel
	Day 4	Hotel	26/12/2026	28/12/2026						Rovaniemi	4 Star, Arctic City Hotel. 2xNight, 1xStandard Double or Twin Room, Incl Brekafast
	Day 4	Activity	26/12/2026							Rovaniemi	"Finnish Arctic Explorer Icebreaker Cruise |Pickup 11:10 AM from Rovaneimi | Drop 17:30 Rovaniemi 
Cruise TIme : 13:15 - 15:45 Swedish / 14:15 - 16:45  | pickup and drop from city centre

ExplorerThe classic icebreaker experience. Float in icy Arctic waters, walk on the frozen sea and earn your cruise certificate.Swimming in survival suitsWalk on the frozen seaComplimentary hot drinkCruise & Swim certificateShuttle bus from Rovaniem"
	Day 8	Activity	30/12/2026							Tromso	"Tromsø: Short Reindeer Sledding, Reindeer Feeding & Sami Culture | 10 AM | 4 hrs 

Pick up / meeting point
Tromsø Havn Prostneset Terminal, Samuel Arnesens gate 5

Overview
Enjoy a traditional Sami experience with a short reindeer sledding ride, reindeer feeding, and a warm meal by the fire, followed by storytelling and joik.

What's included?
Return bus transfer from central Tromsø
Knowledgeable, English-speaking guide
Storytelling and joik performance
Traditional warm Sami meal
Hot drinks and cookies

What to expect?
Enjoy a 10 to 15-minute sledding ride as the reindeer guide you around the valley and along the coast. Afterwards, you will have the opportunity to feed 300 of these magnificent animals before entering the gamme for a hot traditional meal cooked over the fire. Finish the day by gathering around the fire to listen to Sami history, stories and joiking (traditional Sami songs)."
	Day 8	Activity	30/12/2026							Tromso	Tromsø: Northern Lights Safari to Aurora Basecamp | 18:15 | 7 Hrs | Pick-up/drop-off in central Tromsø , English-speaking Northern Lights guide ,Comfortable coach transport with toilet ,Northern Lights instructions video on coach ,Warm overalls and tripods at Base Station ,Snacks, drinks and soup or stew
	Day 10	Activity	01/01/2027							Bergen	"Bergen: Guided Walking Tour of Bergen Past & Present |10:30 | 2 hrs 
 Pick up / meeting point
Bradbenken 1, Bergen

Overview
Discover the stories, landscapes, and local life that shaped Bergen from the Middle Ages to today. This relaxed walk takes you through historic streets, colourful neighbourhoods, and hidden spots most visitors miss, offering a deeper connection with the city.

What's included?
Authorized English-speaking guide
Visit to Bergenhus Fortress
Visit Bryggen Wharf (UNESCO site)
Historic streets and hidden alleys
Scenic viewpoints and backstreets
Local tips on cafes, bars, and restaurants

Not included 
Entrance fees to optional attractions
Transportation to meeting point
Food and drinks are excluded

What to expect?
Visit Bergenhus Fortress, one of Norway’s oldest fortresses, and learn about Norway’s 'Golden Age' when Bergen was the capital. Wander the UNESCO-listed Bryggen Wharf, exploring iconic wooden buildings and over 1000 years of trade history.

Meander through old lanes, courtyards, and cobbled alleys, hearing tales of merchants, fishermen, fires, kings, and everyday life. Your guide will show hidden corners, scenic viewpoints, and charming backstreets away from the crowds."
	Day 11	Transfer 	02/01/2027							Oslo	"Norway in a NUtshell | Bergen to Oslo |08:30 - 22:30 | Including luggage porter service 

08:29 Bergen - 09:41 Voss  Via Scenic Train 
10:10 Voss - 11:10 Gudvangen Via Scenic Bus 
12:00 Gudvangen- 14:00 Flåm Via Scenic Cruise 
16:50 Flåm - 17:30 Myrdal Via Scenic Train
17:40 Myrdal 0 22:27 Oslo Via Scenic Train
"
"""


def _rows_and_grouped():
    rows = normalize_itinerary_rows(parse_itinerary(QG_C_INPUT))
    return rows, group_rows_by_day(rows)


def _day_text(grouped, day):
    return compact_html("\n".join(block["html"] for block in build_day_blocks(grouped[day]) if block))


def test_bergen_walking_tour_identity_is_preserved_and_food_not_invented():
    _, grouped = _rows_and_grouped()
    text = _day_text(grouped, "Day 10")

    assert "Guided Walking Tour of Bergen Past & Present" in text
    assert "Bergen Food & Culture Walk" not in text
    assert "tasting stops" not in text.lower()
    assert "food tour" not in text.lower()
    assert "Bergenhus Fortress" in text
    assert "Bryggen Wharf" in text


def test_norway_in_a_nutshell_timetable_legs_are_cleaned():
    rows, grouped = _rows_and_grouped()
    day_11 = _day_text(grouped, "Day 11")
    source = next(row for row in rows if "Nutshell" in row.get("title", ""))["details"]

    assert extract_norway_nutshell_route_points(source) == ["Bergen", "Voss", "Gudvangen", "Flåm", "Myrdal", "Oslo"]
    legs = extract_norway_nutshell_route_legs(source)
    assert legs[-1] == {
        "departure_time": "5:40 PM",
        "origin": "Myrdal",
        "arrival_time": "10:27 PM",
        "destination": "Oslo",
        "mode": "Scenic Train",
    }
    assert "Myrdal 0 22:27 Oslo" not in day_11
    assert "5:40 PM Myrdal - 10:27 PM Oslo — Scenic Train" in day_11
    assert "Scenic Train Norway in a Nutshell" not in day_11
    assert "Norway in a Nutshell from Bergen to Oslo" in day_11


def test_icebreaker_preserves_timezone_specific_cruise_times():
    _, grouped = _rows_and_grouped()
    text = _day_text(grouped, "Day 4")

    assert "Cruise time: 1:15 PM - 3:45 PM Swedish time / 2:15 PM - 4:45 PM Finnish time" in text
    assert "Pick-up 11:10 AM from Rovaniemi; drop-off 5:30 PM in Rovaniemi" in text


def test_tromso_reindeer_day_does_not_say_lapland():
    _, grouped = _rows_and_grouped()
    text = _day_text(grouped, "Day 8")

    assert "classic Lapland experience" not in text
    assert "Sámi culture and Arctic traditions" in text


def test_journey_arc_does_not_emit_ellipsis_for_tromso_summary():
    _, grouped = _rows_and_grouped()
    arc = create_journey_arc(grouped)
    text = "\n".join(row["experience"] for row in arc)

    assert "..." not in text
    assert "Northern Lights and Sámi culture" in text
    assert "local food culture" not in text.lower()


def test_final_inclusions_keep_correct_bergen_and_clean_nutshell_route():
    rows, grouped = _rows_and_grouped()
    sections = build_inclusion_sections(rows, grouped)
    text = "\n".join(section.title + "\n" + "\n".join(inclusion_item_texts(section)) for section in sections)

    assert "Guided Walking Tour of Bergen Past & Present - 1st of January" in text
    assert "Bergen Food & Culture Walk" not in text
    assert "Myrdal 0 22:27 Oslo" not in text
    assert "Route details:" in text
    assert "5:40 PM Myrdal - 10:27 PM Oslo — Scenic Train" in text
    assert "Scenic Train Norway in a Nutshell" not in text
