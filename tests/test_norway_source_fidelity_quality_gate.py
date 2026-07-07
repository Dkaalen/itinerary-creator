from generator import create_journey_arc, group_rows_by_day
from itinerary_generation.content_validator import compact_html
from itinerary_generation.exclusion_sections import specific_optional_items
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.transport_norway import extract_norway_nutshell_route_legs, extract_norway_nutshell_route_points
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.day_blocks import build_day_blocks


QG_D_INPUT = """
Day 1	Transfer 	15/08/2026									Oslo	Private Airport to Hotel
Day 1	Hotel	15/08/2026	18/08/2026						Oslo	3 Star Comfort Hotel Børsparken, 3xNight , 2 × Family Double room with extra bed, Incl Brekafast  , Room size 22m2
Day 2	Activity	16/08/2026									Oslo	" Oslo : Essential Oslo, City Center Guided Walking Tour | 10 AM | 2 Hrs |

Experience the beauty of the Norwegian capital on foot with this walking tour
See all the major sights and attractions in a pedestrian part of Oslo
Save money with this great value pass

Meet our guide near the University of Oslo,

Start your day with a guided walking tour of Oslo's most popular sights and landmarks.

Explore the major attractions of the vibrant Norwegian capital on our bestselling city tour. Meet our guide near the University of Oslo, in the city’s heart, and embark on a thrilling urban adventure! First, you will visit the modern Oslo Opera House, which quickly became the city’s icon after its construction in 2008.

Next, you will stroll down Karl Johans gate, the city’s emblematic two-lane central street. We will make the first stop on this street near Domkirke, or as the locals gently call this cathedral—the “Dom.”

Follow our guide’s lead and see the other prominent buildings on Oslo’s main street. Stortinget, the Parliament building, the Grand Hotel, the National Theater and the Royal Palace of Oslo are all introduced along the way.

Before the tour concludes, you will visit one more iconic building—the red-brick Oslo City Hall."
Day 3	Activity	17/08/2026									Oslo	"Oslo: Fjord Sightseeing Cruise by 100% Electric Boat |11 AM | 2 hrs

 Pick up / meeting point
Rådhusbrygge 4, Platform E, Oslo

Overview
Embark on a 2-hr Oslofjord Sightseeing Cruise, where history, culture, and natural beauty intertwine. As you sail, discover fortresses, lighthouses, and coastal villages that echo with centuries-old tales. Audio guides available to enhance your experience.

What's included?
Oslo Fjord archipelago cruise by electric boat
Cafeteria with snacks and drinks for purchase
""Voice of Norway"" Audio guide for download
Stop at the Bygdøy peninsula near to museums

What to expect?
Discover the scenic Oslo’s fjord in a 2-hour sightseeing cruise onboard of 100% electric, silent boat Oslofjord I. When you sail from the city center – Rådhusbrygga 4 in Oslo, you have a great view of the city’s coastline with its impressive architecture and historical sites: Akershus fortress, the Opera house and the Munch Museum."
Day 3	Activity	17/08/2026									Oslo	Optional  Upgradesd avaiable in Oslo
Day 4	Activity	18/08/2026									Gudvangen	"Norway in a Nutshell  Tour | Enjoy Scenic Train, Cruise and bus combo in one beautiful journey

09:18 Oslo
14:20 Myrdal via train
14:41 Myrdal
15:39 Flåm Via train
17:30 Flåm
19:20 Gudvangen Via Cruise

Highlights : Your tour starts in Oslo , The Bergen Railway, The Flåm Railway, UNESCO Nærøyfjord Cruise, Bus trip through Nærøydalen valley , Gudvangen is a tiny village nestled in the Nærøyfjord."
Day 4	Hotel	18/08/2026	19/08/2026						Gudvangen	3 Star ,Gudvangen Fjordtell , 1xNight , 3xStandard Double Room (Viking), Incl Brekafast , 16 m2
Day 5	Activity	19/08/2026									Bergen	"Norway in a Nuthsell Part 2
11:40 Gudvangen
12:40 Voss Via Scenic bus
13:02 Voss
14:15 Bergen via Train

Highlights :The Voss Railway , Voss is one of the most ""active"" towns in Norway, known for outdoor adventures and action sports. Your tour ends in Bergen"
Day 5	Hotel	19/08/2026	21/08/2026						Bergen	3Star ,Scandic Byparken , 2xNight ,2x Family   Triple Room 3 TwinBeds , Incl Brekafast  18m2
Day 6	Activity	20/08/2026									Bergen	"Bergen : Must-See Bergen on Foot and Boat | 10:30 AM | 2 Hrs |

Pick up / meeting point
Strandkaien 3, Bergen

Overview
This 2-in-1 tour offers the ultimate Bergen experience, combining history, culture, and fjord exploration. Stroll through the alleys of the old timber town, hear fascinating stories about the city and its people, and discover centuries of history.

What's included?
Authorized, English-speaker guide
Guided walking tour of Bergen
City cruise with panoramic views
Visit to Bergen Bryggen UNESCO area
Visit to Bergen Fish Market
Visit to St. Mary's Church

What to expect?
Explore the city’s highlights, including the famed Fish Market, iconic waterfront buildings, and St. Mary’s Church, Bergen’s oldest existing building. Finish your experience with a 30-minute boat ride, offering panoramic views and a fresh perspective of Bergen from the water."
Day 6	Activity	20/08/2026									Bergen	"Bergen Roundtrip Fløibanen Tickets | The Fløibanen funicular in Bergen is one of Norway’s best-known and most visited attractions. The journey up to Fløyen (320 m above sea level) takes about 5–8 minutes.

Meeting Point : Vetrlidsallmenningen 23A, 5014 "
Day 7	Transfer 	21/08/2026									Bergen	Private Hotel to Airport
"""


def _rows_and_grouped():
    rows = normalize_itinerary_rows(parse_itinerary(QG_D_INPUT))
    return rows, group_rows_by_day(rows)


def _day_text(grouped, day):
    return compact_html("\n".join(block["html"] for block in build_day_blocks(grouped[day]) if block))


def test_oslofjord_cruise_identity_beats_incidental_munch_museum_mentions():
    _, grouped = _rows_and_grouped()
    text = _day_text(grouped, "Day 3")

    assert "Fjord Sightseeing Cruise by 100% Electric Boat" in text
    assert "Munch Museum Visit" not in text
    assert "Visit the Munch Museum" not in text
    assert "Oslofjord" in text
    assert "electric boat" in text.lower()


def test_split_norway_in_a_nutshell_days_render_as_route_travel_not_generic_activity():
    rows, grouped = _rows_and_grouped()
    day_4 = _day_text(grouped, "Day 4")
    day_5 = _day_text(grouped, "Day 5")

    day_4_source = next(row for row in rows if row.get("day") == "Day 4" and "Nutshell" in row.get("title", ""))["details"]
    day_5_source = next(row for row in rows if row.get("day") == "Day 5" and "Nutshell" in row.get("original_title", "") + row.get("details", ""))["details"]

    assert extract_norway_nutshell_route_points(day_4_source) == ["Oslo", "Myrdal", "Flåm", "Gudvangen"]
    assert extract_norway_nutshell_route_legs(day_4_source) == [
        {"departure_time": "9:18 AM", "origin": "Oslo", "arrival_time": "2:20 PM", "destination": "Myrdal", "mode": "Train"},
        {"departure_time": "2:41 PM", "origin": "Myrdal", "arrival_time": "3:39 PM", "destination": "Flåm", "mode": "Train"},
        {"departure_time": "5:30 PM", "origin": "Flåm", "arrival_time": "7:20 PM", "destination": "Gudvangen", "mode": "Cruise"},
    ]
    assert "9:18 AM Oslo - 2:20 PM Myrdal — Train" in day_4
    assert "5:30 PM Flåm - 7:20 PM Gudvangen — Cruise" in day_4

    assert extract_norway_nutshell_route_points(day_5_source) == ["Gudvangen", "Voss", "Bergen"]
    assert "Guided experience in Bergen" not in day_5
    assert "Travel Arrangements" in day_5
    assert "Norway in a Nutshell to Bergen" in day_5
    assert "11:40 AM Gudvangen - 12:40 PM Voss — Scenic Bus" in day_5
    assert "1:02 PM Voss - 2:15 PM Bergen — Train" in day_5


def test_oslo_walking_and_bergen_boat_descriptions_keep_real_activity_facts():
    _, grouped = _rows_and_grouped()
    day_2 = _day_text(grouped, "Day 2")
    day_6 = _day_text(grouped, "Day 6")

    assert "Oslo Opera House" in day_2
    assert "Royal Palace" in day_2
    assert "Oslo City Hall" in day_2

    assert "Bergen Walking & Boat Tour" in day_6
    assert "30-minute boat ride" in day_6 or "by boat" in day_6
    assert "Authorized English-speaking guide" in day_6
    assert "English-speaker guide" not in day_6


def test_optional_upgrade_title_and_journey_arc_are_clean():
    rows, grouped = _rows_and_grouped()
    optional_items = specific_optional_items(rows)
    arc_text = "\n".join(row["experience"] for row in create_journey_arc(grouped))

    assert optional_items == ["Optional Upgrades - 17th of August"]
    assert "Optional Upgradesd avaiable" not in "\n".join(optional_items)
    assert "City sights and Oslofjord cruising" in arc_text
    assert "Fjord scenery and coastal cruising" not in arc_text


def test_final_inclusions_keep_cruise_and_split_nutshell_parts():
    rows, grouped = _rows_and_grouped()
    sections = create_categorized_inclusions(rows, grouped)
    text = "\n".join(section["title"] + "\n" + "\n".join(section.get("items", [])) for section in sections)

    assert "Fjord Sightseeing Cruise by 100% Electric Boat - 17th of August" in text
    assert "Munch Museum Visit" not in text
    assert "Norway in a Nutshell to Gudvangen" in text
    assert "Norway in a Nutshell to Bergen" in text
    assert "11:40 AM Gudvangen - 12:40 PM Voss — Scenic Bus" in text
