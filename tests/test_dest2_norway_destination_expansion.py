from __future__ import annotations

from collections import Counter

from images.matcher_context import build_day_context
from images.metadata import city_variants
from itinerary_generation.destination_registry import (
    destination_for_alias,
    registry_records,
    travel_destination_records,
)
from place_alias_queries import country_for_place, is_known_place, kind_for_place


def _norway_records():
    return [record for record in registry_records() if record.country == "Norway"]


def test_norway_registry_expands_towards_full_destination_intelligence_layer():
    norway = _norway_records()
    counts = Counter(record.destination_type for record in norway)

    assert len(norway) >= 160
    assert counts["village"] >= 25
    assert counts["town"] >= 60
    assert counts["resort"] >= 10
    assert counts["island"] >= 10
    assert counts["national_park"] >= 5


def test_norway_expansion_includes_itinerary_relevant_hubs_and_gateways():
    expected = {
        "Geilo",
        "Finse",
        "Odda",
        "Eidfjord",
        "Loen",
        "Olden",
        "Hellesylt",
        "Røros",
        "Oppdal",
        "Henningsvær",
        "Andenes",
        "Hammerfest",
        "Jotunheimen",
        "Hardangervidda",
    }
    names = {record.name for record in _norway_records()}

    assert expected <= names


def test_expanded_norway_destinations_are_available_to_parser_alias_lookup():
    samples = {
        "Hjorundfjord": ("Hjørundfjord", "fjord"),
        "Jorpeland": ("Jørpeland", "town"),
        "Beitostolen": ("Beitostølen", "resort"),
        "Henningsvaer": ("Henningsvær", "village"),
        "Hardangervidda National Park": ("Hardangervidda", "national_park"),
    }

    for alias, (canonical, kind) in samples.items():
        assert is_known_place(alias)
        assert destination_for_alias(alias).name == canonical
        assert country_for_place(alias) == "Norway"
        assert kind_for_place(alias) == kind


def test_expanded_norway_destinations_feed_image_context_country_and_variants():
    assert "henningsvaer" in city_variants("Henningsvær")

    context = build_day_context(
        "Day 1",
        [
            {
                "day": "Day 1",
                "date": "18.09.2026",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Henningsvær",
                "title": "Henningsvær harbour walk",
                "details": "Explore the fishing village and coastal viewpoints.",
            }
        ],
    )

    assert context["city"] == "Henningsvær"
    assert "norway" in context["country_variants"]
