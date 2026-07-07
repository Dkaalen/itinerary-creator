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


def _finland_records():
    return [record for record in registry_records() if record.country == "Finland"]


def test_finland_registry_expands_towards_full_destination_intelligence_layer():
    finland = _finland_records()
    counts = Counter(record.destination_type for record in finland)

    assert len(finland) >= 120
    assert counts["city"] >= 20
    assert counts["town"] >= 45
    assert counts["resort"] >= 12
    assert counts["island"] >= 5
    assert counts["national_park"] >= 10


def test_finland_expansion_includes_itinerary_relevant_hubs_and_gateways():
    expected = {
        "Espoo",
        "Hanko",
        "Fiskars",
        "Kotka",
        "Naantali",
        "Mariehamn",
        "Archipelago Sea",
        "Koli",
        "Koli National Park",
        "Vuokatti",
        "Ruka",
        "Kemijärvi",
        "Äkäslompolo",
        "Kilpisjärvi",
        "Pallas-Yllästunturi",
        "Urho Kekkonen",
    }
    names = {record.name for record in _finland_records()}

    assert expected <= names


def test_expanded_finland_destinations_are_available_to_parser_alias_lookup():
    samples = {
        "Jarvenpaa": ("Järvenpää", "town"),
        "Ekenas": ("Tammisaari", "town"),
        "Parainen": ("Pargas", "town"),
        "Iso Syote": ("Iso-Syöte", "resort"),
        "Urho Kekkonen National Park": ("Urho Kekkonen", "national_park"),
        "Pallas-Yllastunturi National Park": ("Pallas-Yllästunturi", "national_park"),
    }

    for alias, (canonical, kind) in samples.items():
        assert is_known_place(alias)
        assert destination_for_alias(alias).name == canonical
        assert country_for_place(alias) == "Finland"
        assert kind_for_place(alias) == kind


def test_expanded_finland_destinations_feed_image_context_country_and_variants():
    assert "akäslompolo" not in city_variants("Äkäslompolo")
    assert "akaslompolo" in city_variants("Äkäslompolo")

    context = build_day_context(
        "Day 1",
        [
            {
                "day": "Day 1",
                "date": "18.09.2026",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Äkäslompolo",
                "title": "Äkäslompolo village and fell scenery",
                "details": "Explore Lapland fell views, trails and village atmosphere.",
            }
        ],
    )

    assert context["city"] == "Äkäslompolo"
    assert "finland" in context["country_variants"]


def test_finland_profiles_distinguish_southern_coastal_and_arctic_image_needs():
    assert is_southern_coastal_destination("Helsinki")
    assert is_southern_coastal_destination("Hanko")
    assert is_southern_coastal_destination("Turku Archipelago")

    rovaniemi = destination_for_alias("Rovaniemi")
    pallas = destination_for_alias("Pallas-Yllastunturi National Park")
    assert rovaniemi.season_profile == "arctic"
    assert pallas.image_profile == "arctic"
