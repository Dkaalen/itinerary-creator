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


def _sweden_records():
    return [record for record in registry_records() if record.country == "Sweden"]


def test_sweden_registry_expands_towards_full_destination_intelligence_layer():
    sweden = _sweden_records()
    counts = Counter(record.destination_type for record in sweden)

    assert len(sweden) >= 110
    assert counts["city"] >= 20
    assert counts["town"] >= 35
    assert counts["resort"] >= 8
    assert counts["island"] >= 8
    assert counts["national_park"] >= 8


def test_sweden_expansion_includes_itinerary_relevant_hubs_and_gateways():
    expected = {
        "Lund",
        "Helsingborg",
        "Kalmar",
        "Karlskrona",
        "Marstrand",
        "Fjällbacka",
        "Smögen",
        "Sälen",
        "Idre",
        "Riksgränsen",
        "Björkliden",
        "Gällivare",
        "Jokkmokk",
        "Sarek",
        "Padjelanta",
        "Höga Kusten",
    }
    names = {record.name for record in _sweden_records()}

    assert expected <= names


def test_expanded_sweden_destinations_are_available_to_parser_alias_lookup():
    samples = {
        "Fjallbacka": ("Fjällbacka", "village"),
        "Smogen": ("Smögen", "village"),
        "Riksgransen": ("Riksgränsen", "resort"),
        "Gallivare": ("Gällivare", "town"),
        "High Coast Sweden": ("Höga Kusten", "region"),
        "Padjelanta National Park": ("Padjelanta", "national_park"),
    }

    for alias, (canonical, kind) in samples.items():
        assert is_known_place(alias)
        assert destination_for_alias(alias).name == canonical
        assert country_for_place(alias) == "Sweden"
        assert kind_for_place(alias) == kind


def test_expanded_sweden_destinations_feed_image_context_country_and_variants():
    assert "fjallbacka" in city_variants("Fjällbacka")

    context = build_day_context(
        "Day 1",
        [
            {
                "day": "Day 1",
                "date": "18.09.2026",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Fjällbacka",
                "title": "Fjällbacka coastal village walk",
                "details": "Explore the harbour, smooth granite coast and west-coast streets.",
            }
        ],
    )

    assert context["city"] == "Fjällbacka"
    assert "sweden" in context["country_variants"]


def test_sweden_profiles_distinguish_coastal_and_arctic_image_needs():
    assert is_southern_coastal_destination("Gothenburg")
    assert is_southern_coastal_destination("Fjallbacka")

    kiruna = destination_for_alias("Kiruna")
    abisko = destination_for_alias("Abisko National Park")
    assert kiruna.season_profile == "arctic"
    assert abisko.image_profile == "arctic"
