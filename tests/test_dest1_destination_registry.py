from __future__ import annotations

from itinerary_generation.destination_registry import (
    destination_country_for_alias,
    destination_for_alias,
    is_southern_coastal_destination,
    registry_city_aliases,
    registry_records,
    travel_destination_records,
)
from place_alias_data import PLACES


def test_destination_registry_preserves_legacy_place_contract():
    records = registry_records()

    assert len(records) == len(PLACES)
    assert {record.name for record in records} >= {"Oslo", "Bergen", "Flåm", "Norway in a Nutshell"}
    assert destination_for_alias("Tromso").name == "Tromsø"
    assert destination_country_for_alias("BGO") == "norway"


def test_destination_registry_records_have_operational_profiles():
    travel_records = travel_destination_records()

    assert travel_records
    for record in travel_records:
        assert record.country
        assert record.region
        assert record.destination_type
        assert record.season_profile
        assert record.image_profile
        assert record.copy_profile
        assert record.transport_role
        assert record.priority > 0


def test_registry_city_aliases_feed_image_matching_aliases():
    aliases = registry_city_aliases()

    assert "flam" in aliases
    assert "Flåm" in aliases["flam"]
    assert "Kristiansand" in aliases["kristiansand"]


def test_southern_coastal_profile_is_registry_driven():
    assert is_southern_coastal_destination("Bergen")
    assert is_southern_coastal_destination("Kristiansand")
    assert is_southern_coastal_destination("Stavanger")
    assert not is_southern_coastal_destination("Tromsø")
