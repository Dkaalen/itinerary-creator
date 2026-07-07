from __future__ import annotations

from collections import Counter

from images.matcher_context import build_day_context
from images.metadata import city_variants
from itinerary_generation.destination_registry import (
    destination_for_alias,
    is_southern_coastal_destination,
    registry_records,
)
from place_alias_queries import country_for_place, is_known_place, kind_for_place


def _denmark_records():
    return [record for record in registry_records() if record.country == "Denmark"]


def test_denmark_registry_expands_towards_full_destination_intelligence_layer():
    denmark = _denmark_records()
    counts = Counter(record.destination_type for record in denmark)

    assert len(denmark) >= 105
    assert counts["city"] >= 10
    assert counts["town"] >= 55
    assert counts["island"] >= 12
    assert counts["national_park"] >= 3


def test_denmark_expansion_includes_itinerary_relevant_hubs_and_gateways():
    expected = {
        "Dragør",
        "Køge",
        "Møn",
        "Møns Klint",
        "Lolland",
        "Falster",
        "Ærøskøbing",
        "Svendborg",
        "Samsø",
        "Fanø",
        "Rømø",
        "Sønderborg",
        "Silkeborg",
        "Ebeltoft",
        "Mols Bjerge",
        "National Park Thy",
        "Rønne",
        "Wadden Sea National Park",
        "Kongernes Nordsjælland",
    }
    names = {record.name for record in _denmark_records()}

    assert expected <= names


def test_expanded_denmark_destinations_are_available_to_parser_alias_lookup():
    samples = {
        "Dragor": ("Dragør", "town"),
        "Moens Klint": ("Møns Klint", "attraction"),
        "Aeroeskoebing": ("Ærøskøbing", "town"),
        "Mols Bjerge National Park": ("Mols Bjerge", "national_park"),
        "Nationalpark Thy": ("National Park Thy", "national_park"),
        "Royal North Zealand National Park": ("Kongernes Nordsjælland", "national_park"),
    }

    for alias, (canonical, kind) in samples.items():
        assert is_known_place(alias)
        assert destination_for_alias(alias).name == canonical
        assert country_for_place(alias) == "Denmark"
        assert kind_for_place(alias) == kind


def test_expanded_denmark_destinations_feed_image_context_country_and_variants():
    assert "aeroskobing" in city_variants("Ærøskøbing")
    assert "aeroeskoebing" in city_variants("Ærøskøbing")

    context = build_day_context(
        "Day 1",
        [
            {
                "day": "Day 1",
                "date": "18.09.2026",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Ærøskøbing",
                "title": "Ærøskøbing island village walk",
                "details": "Explore cobbled lanes, colourful houses and the small harbour atmosphere.",
            }
        ],
    )

    assert context["city"] == "Ærøskøbing"
    assert "denmark" in context["country_variants"]


def test_denmark_profiles_distinguish_southern_coastal_and_island_image_needs():
    assert is_southern_coastal_destination("Copenhagen")
    assert is_southern_coastal_destination("Skagen")
    assert is_southern_coastal_destination("Aeroeskoebing")

    copenhagen = destination_for_alias("Copenhagen")
    bornholm = destination_for_alias("Ronne")
    thy = destination_for_alias("Nationalpark Thy")

    assert copenhagen.region == "Greater Copenhagen"
    assert bornholm.region == "Bornholm"
    assert thy.image_profile == "national_park"
