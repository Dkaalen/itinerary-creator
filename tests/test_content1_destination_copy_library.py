from __future__ import annotations

from itinerary_generation.destination_copy import (
    destination_arc_fallback,
    leisure_description,
    travel_day_intro,
)
from itinerary_generation.destination_registry import travel_destination_records


BAD_FALLBACK_BITS = (
    "Time at leisure",
    "quiet walk nearby",
    "Spend time at leisure",
    "Travel towards",
)


def test_content1_all_registered_destinations_have_premium_arc_and_leisure_copy():
    records = travel_destination_records()

    assert len(records) >= 600
    for record in records:
        arc = destination_arc_fallback(record.name)
        leisure = leisure_description(record.name, [])

        assert arc
        assert leisure
        assert arc != f"Discover {record.name}"
        assert "Time at leisure" not in arc
        assert "Time at leisure" not in leisure
        assert "quiet walk nearby" not in leisure
        assert record.name in leisure


def test_content1_priority_destinations_keep_curated_copy():
    expected = {
        "Oslo": "Discover the Norwegian capital",
        "Kristiansand": "Southern coastal charm",
        "Stavanger": "Stavanger harbour and fjord gateway",
        "Bergen": "Bergen harbour and mountain views",
        "Flåm": "Fjord village and railway scenery",
        "Rovaniemi": "Lapland forest and Arctic Circle atmosphere",
        "Vík": "Black-sand coast and South Iceland scenery",
        "Landmannalaugar": "Highland colours and rhyolite mountains",
    }

    for city, phrase in expected.items():
        assert destination_arc_fallback(city) == phrase


def test_content1_leisure_copy_avoids_already_covered_activity_themes():
    text = leisure_description(
        "Bergen",
        [
            {"city": "Bergen", "type": "Activity", "title": "Guided walking tour of Bergen Past & Present"},
            {"city": "Bergen", "type": "Activity", "title": "Fløybanen Funicular Experience"},
        ],
    )

    assert "colourful lanes" not in text
    assert "mountain viewpoints" not in text
    assert "the harbourfront" in text


def test_content1_generic_travel_intro_uses_destination_profile():
    kristiansand = travel_day_intro("Oslo", "Kristiansand", "coach")
    rovaniemi = travel_day_intro("Helsinki", "Rovaniemi", "train")
    vik = travel_day_intro("Reykjavík", "Vík", "self-drive")

    assert "Kristiansand’s coastal setting" in kristiansand
    assert "Rovaniemi’s Arctic landscapes" in rovaniemi
    assert "Vík’s Icelandic landscapes" in vik
    for phrase in (kristiansand, rovaniemi, vik):
        assert "laid out clearly" not in phrase
        assert "Travel towards" not in phrase
