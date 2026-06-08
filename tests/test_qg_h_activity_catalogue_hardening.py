from generator import group_rows_by_day
from itinerary_generation.quality_gate import evaluate_client_output_quality
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.render_document_builder import build_render_document
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from text_polish import polish_client_text


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def _render(rows):
    return build_render_document(rows, group_rows_by_day(rows))


def test_bergen_guided_flam_day_tour_is_not_norway_in_a_nutshell_false_positive():
    raw = '''
Day 1	Activity	01/06/2026							Bergen	"Bergen: Guided Day Tour to Flåm incl. Flåm Railway & Fjord Cruise | 07:45 AM | 10.5 Hrs
Pick up / meeting point : Guided Fjord Tours Office, Strandkaien 16, Bergen
Overview
Explore the best of Norway's natural beauty on our guided discovery tours to the Nærøyfjord and Flåm Railway.
What's included?
Knowledgeable, English-speaking guide
Panorama coach, Bergen to Gudvangen
Premium fjord cruise, Gudvangen to Flåm
Flåm Railway, Flåm to Myrdal
Bergen Railway, Myrdal to Voss
Panorama coach, Voss to Bergen"
'''
    rows = _rows(raw)

    assert rows[0]["title"] == "Bergen Guided Day Tour to Flåm with Flåm Railway & Fjord Cruise"
    assert rows[0]["activity_product"]["canonical_family"] == "bergen_guided_flam_day_tour"
    assert rows[0]["activity_product"]["product_type"] == "guided_scenic_day_tour"
    assert rows[0]["effective_type"] != "Transport"
    assert "Norway in a Nutshell" not in rows[0]["title"]


def test_aurora_wording_is_review_warning_not_client_output_blocker():
    raw = '''
Day 1	Activity	01/06/2026							Rovaniemi	"Rovaniemi: Snowmobile Evening Safari & Aurora Opportunity | 19:00 | 5 HRS
Overview
Ride brand-new snowmobiles across private forest and tundra trails under Lapland's Arctic night sky.
What's included?
Pick-up/drop-off in central Rovaniemi
Professional snowmobile guidance
Northern Lights viewing opportunity"
'''
    rows = _rows(raw)
    render_document = _render(rows)
    report = evaluate_client_output_quality(render_document)

    assert rows[0]["activity_product"]["canonical_family"] == "snowmobile_evening_safari"
    assert "Aurora" in rows[0]["title"] or "Northern Lights" in rows[0]["title"]
    assert "forbidden_aurora_wording" not in {issue.code for issue in report.blocking_issues}
    assert "aurora_wording_review" in {issue.code for issue in report.warnings}


def test_more_ticket_and_admission_products_receive_fingerprints():
    raw = '''
Day 1	Activity	01/06/2026							Oslo	MUNCH Museum Entrance Tickets | Time: Flexible | Includes: Admission tickets
Day 2	Activity	02/06/2026							Stockholm	Vasa Museum Entrance Tickets | Time: Flexible | Includes: Admission tickets
Day 3	Activity	03/06/2026							Stockholm	Stockholm City Highlights Boat Tour |Meeting Point :  Strömkajen, Stromma Ticketshop Gate C | 2 h 15 Min | 12:00
Day 4	Activity	04/06/2026							Copenhagen	Copenhagen Canal Cruise | 11 AM | 1 Hr | Includes: Canal boat cruise
Day 5	Activity	05/06/2026							Tromso	Tromso Cable Car Round Trip Ticket : Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening.
'''
    rows = _rows(raw)
    families = [row.get("activity_product", {}).get("canonical_family") for row in rows]

    assert families == [
        "munch_museum_ticket",
        "vasa_museum_ticket",
        "stockholm_city_highlights_boat",
        "copenhagen_canal_cruise",
        "tromso_cable_car_ticket",
    ]
    assert [row.get("activity_product", {}).get("product_type") for row in rows] == [
        "admission",
        "admission",
        "boat_tour",
        "canal_cruise",
        "ticket",
    ]


def test_activity_typo_cleanup_catches_extra_common_supplier_typos():
    text = polish_client_text(
        "Tallinnn, Hlesinkih, Reyakjvik, VIllage, Santa CLaus, Afternon, "
        "Melas onboard, avaiable and arrnaged with additonal ticktes"
    )

    assert "Tallinn" in text
    assert "Helsinki" in text
    assert "Reykjavík" in text
    assert "Village" in text
    assert "Santa Claus" in text
    assert "Afternoon" in text
    assert "Meals onboard" in text
    assert "available and arranged with additional tickets" in text
