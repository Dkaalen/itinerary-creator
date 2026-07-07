from __future__ import annotations

from collections import Counter

from images.matcher_context import build_day_context
from images.metadata import city_variants
from itinerary_generation.destination_registry import destination_for_alias, registry_records
from place_alias_queries import country_for_place, is_known_place, kind_for_place


def _iceland_records():
    return [record for record in registry_records() if record.country == "Iceland"]


def test_iceland_registry_expands_towards_full_destination_intelligence_layer():
    iceland = _iceland_records()
    counts = Counter(record.destination_type for record in iceland)

    assert len(iceland) >= 120
    assert counts["town"] >= 35
    assert counts["village"] >= 18
    assert counts["region"] >= 20
    assert counts["national_park"] >= 5
    assert counts["route"] >= 4


def test_iceland_expansion_includes_ring_road_highland_and_cruise_port_hubs():
    expected = {
        "Reykjanes Peninsula",
        "Grindavík",
        "Hveragerði",
        "Hella",
        "Þórsmörk",
        "Kirkjubæjarklaustur",
        "Öræfi",
        "Grundarfjörður",
        "Snæfellsjökull",
        "Hornstrandir",
        "Siglufjörður",
        "Reykjahlíð",
        "Ásbyrgi",
        "Djúpivogur",
        "Borgarfjörður Eystri",
        "Kerlingarfjöll",
        "Hveravellir",
        "Ring Road",
    }
    names = {record.name for record in _iceland_records()}

    assert expected <= names


def test_expanded_iceland_destinations_are_available_to_parser_alias_lookup():
    samples = {
        "Thorsmork": ("Þórsmörk", "region"),
        "Kirkjubaejarklaustur": ("Kirkjubæjarklaustur", "village"),
        "Snaefellsjokull National Park": ("Snæfellsjökull", "national_park"),
        "Bakkagerdi": ("Borgarfjörður Eystri", "village"),
        "Route 1": ("Ring Road", "route"),
        "Isafjordur Airport": ("Ísafjörður Airport", "airport"),
    }

    for alias, (canonical, kind) in samples.items():
        assert is_known_place(alias)
        assert destination_for_alias(alias).name == canonical
        assert country_for_place(alias) == "Iceland"
        assert kind_for_place(alias) == kind


def test_expanded_iceland_destinations_feed_image_context_country_and_variants():
    assert "thorsmork" in city_variants("Þórsmörk")
    assert "kirkjubaejarklaustur" in city_variants("Kirkjubæjarklaustur")

    context = build_day_context(
        "Day 1",
        [
            {
                "day": "Day 1",
                "date": "18.09.2026",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Þórsmörk",
                "title": "Þórsmörk highland valley walk",
                "details": "Explore Icelandic highland scenery between glaciers, ridges and river valleys.",
            }
        ],
    )

    assert context["city"] == "Þórsmörk"
    assert "iceland" in context["country_variants"]


def test_iceland_profiles_distinguish_city_highland_route_and_cruise_port_needs():
    reykjavik = destination_for_alias("Reykjavik")
    thorsmork = destination_for_alias("Thorsmork")
    ring_road = destination_for_alias("Iceland Ring Road")
    isafjordur = destination_for_alias("Isafjordur")

    assert reykjavik.region == "Capital Region"
    assert reykjavik.image_profile == "cruise_port"
    assert thorsmork.season_profile == "iceland_all_season"
    assert ring_road.image_profile == "iceland_route"
    assert "cruise_port" in isafjordur.transport_role
