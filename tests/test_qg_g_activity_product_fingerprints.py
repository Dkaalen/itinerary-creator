from generator import group_rows_by_day
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from text_polish import polish_client_text


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_optional_addon_prefix_preserves_real_product_title_and_optional_status():
    raw = """
Day 1	Activity	01/06/2026									"Optinal addon on request | Tromsø: Reindeer Feeding and Sami Culture | 10 AM | 5 Hrs"
Day 2	Activity	02/06/2026								Alesund	Addon Optional Activity at additonal cost : Geiranger Fjord Cruise Day Trip
"""
    rows = _rows(raw)

    assert rows[0]["commercial_status"] == "optional"
    assert rows[0]["title"] == "Reindeer Feeding and Sámi Culture"
    assert rows[0]["activity_product"]["canonical_family"] == "tromso_reindeer_sami"

    assert rows[1]["commercial_status"] == "optional"
    assert rows[1]["title"] == "Geiranger Fjord Cruise Day Trip"
    assert rows[1]["activity_product"]["canonical_family"] == "geiranger_fjord_cruise"


def test_floibanen_ticket_row_uses_ticket_identity_not_generic_guided_experience():
    raw = """
Day 1	Activity	01/06/2026									Bergen Roundtrip Fløibanen Tickets | The Fløibanen funicular in Bergen is one of Norway’s best-known and most visited attractions. The journey up to Fløyen (320 m above sea level) takes about 5–8 minutes.
Day 2	Activity	02/06/2026									Bergen: Fløibanen Funicual - Time: Flexible - Meeting point: Vetrlidsallmenningen 23A - Includes: Tickets
"""
    rows = _rows(raw)

    assert [row["title"] for row in rows] == ["Fløibanen Funicular", "Fløibanen Funicular"]
    assert all(row["activity_product"]["product_type"] == "ticket" for row in rows)
    assert "Guided experience" not in " ".join(row["title"] for row in rows)


def test_bergen_city_drive_highlight_mentions_do_not_override_supplier_title():
    raw = """
Day 1	Activity	01/06/2026		Bergen: Private Bergen City Drive - Time: 09:00 am - 12:00 pm - Meeting point: Hotel pick up - Includes: All transport modes, including fuel and tolls - Highlights: Bergen historical core, Mt Fløyen roads, waterfall
"""
    rows = _rows(raw)

    assert rows[0]["title"] == "Private Bergen City Drive"
    assert rows[0]["activity_product"]["canonical_family"] == "bergen_city_drive"
    assert rows[0]["activity_product"]["product_type"] == "private_drive"
    assert rows[0]["activity_product"]["display_title"] == "Private Bergen City Drive"


def test_norway_in_a_nutshell_typos_keep_clean_route_and_structured_legs():
    raw = """
Day 1	Activity	01/06/2026								Oslo	Oslo to Bergen | Norway in a NUtsheel 08:25 - 20:40 | Including Luggage porter service
Day 2	Activity	02/06/2026								Bergen	"Oslo: Norway in a Nutshell  to Bergen - Includes: Tickets with Luggages porter service 
08:25 Oslo
13:04 Myrdal
13:24 Myrdal
14:22 Flåm
15:00 Flåm
17:00 Gudvangen
17:25 Gudvangen
18:25 Voss
19:14 Voss
20:38 Bergen"
"""
    rows = _rows(raw)

    assert rows[0]["effective_type"] == "Transport"
    assert rows[0]["title"] == "Norway in a Nutshell from Oslo to Bergen"
    assert "Oslo to Bergen Oslo to Bergen" not in rows[0]["title"]
    assert rows[0]["activity_product"]["canonical_family"] == "norway_in_a_nutshell"
    assert rows[0]["activity_product"]["product_type"] == "scenic_route"

    assert rows[1]["title"] == "Norway in a Nutshell to Bergen"
    assert rows[1]["activity_product"]["variant_tags"] == ["luggage_service"]
    assert [leg["origin"] for leg in rows[1]["route_legs"]] == ["Oslo", "Myrdal", "Flåm", "Gudvangen", "Voss"]
    assert [leg["destination"] for leg in rows[1]["route_legs"]][-1] == "Bergen"


def test_activity_product_metadata_survives_into_structured_document():
    raw = """
Day 1	Activity	01/06/2026								Oslo	"Oslo: Fjord Sightseeing Cruise by 100% Electric Boat | 11 AM | 2 Hrs
Pick up / meeting point : Rådhusbrygge 4, Platform E, Oslo
What's included?
Oslo Fjord archipelago cruise by electric boat
Voice of Norway Audio guide for download
Stop at the Bygdøy peninsula near to museums"
"""
    rows = _rows(raw)
    document = build_itinerary_document(rows, group_rows_by_day(rows))
    item = document.items[0]

    assert rows[0]["title"] == "Fjord Sightseeing Cruise by 100% Electric Boat"
    assert rows[0]["activity_product"]["canonical_family"] == "oslofjord_cruise"
    assert item.metadata["activity_product"]["canonical_family"] == "oslofjord_cruise"
    assert item.metadata["activity_product"]["variant_tags"] == ["bygdoy_stop", "audio_guide", "electric_boat"]


def test_activity_typo_cleanup_is_shared_for_client_text():
    text = polish_client_text("Tallin, Helisnki, Reykajvik, Tromso, Alesund, FLam, Kakslauttenen, Saariselka, NUtsheel, Profesional Engish ticktes at additonal cost")

    assert "Tallinn" in text
    assert "Helsinki" in text
    assert "Reykjavík" in text
    assert "Tromsø" in text
    assert "Ålesund" in text
    assert "Flåm" in text
    assert "Kakslauttanen" in text
    assert "Saariselkä" in text
    assert "Nutshell" in text
    assert "Professional English tickets at additional cost" in text
