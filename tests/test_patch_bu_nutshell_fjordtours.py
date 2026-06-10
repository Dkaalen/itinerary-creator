from __future__ import annotations

from itinerary_generation.activity_products import fingerprint_activity
from itinerary_generation.fjordtours_activity_catalogue import (
    FJORDTOURS_NUTSHELL_ADDON_ACTIVITIES,
    fjordtours_activity_description,
)
from itinerary_generation.product_rules import find_product_match
from itinerary_generation.title_routes import _route_label_from_activity_text
from itinerary_generation.transport_norway import (
    explicit_norway_nutshell_title,
    extract_norway_nutshell_route_points,
    is_nutshell_internal_route_node,
)
from itinerary_generation.transport import get_transport_route_phrase
from normalizer import normalize_itinerary_rows
from parser_modules.parser_main import parse_itinerary


def test_patch_bu_gudvangen_is_valid_explicit_nutshell_destination() -> None:
    source = "Gudvangen: Norway in a Nutshell to Gudvangen - Includes: Train Oslo to Myrdal, Flåm Railway Myrdal to Flåm, Fjord Cruise Flåm to Gudvangen"

    assert explicit_norway_nutshell_title(source) == "Norway in a Nutshell to Gudvangen"
    assert _route_label_from_activity_text(source) == "Norway in a Nutshell to Gudvangen"
    assert not is_nutshell_internal_route_node("Gudvangen")


def test_patch_bu_includes_only_gudvangen_does_not_override_bergen_destination() -> None:
    source = "Norway in a Nutshell to Bergen - Includes: Fjord Cruise Flåm to Gudvangen, Coach Transfer Gudvangen to Voss, Train transfer Voss to Bergen"

    assert _route_label_from_activity_text(source) == "Norway in a Nutshell to Bergen"

    rows = normalize_itinerary_rows(parse_itinerary(f"Day 1\tActivity\t01.06.2026\t\tFlåm: {source}"))
    nutshell = next(row for row in rows if "Norway in a Nutshell" in row.get("title", ""))
    assert nutshell["title"] == "Norway in a Nutshell to Bergen"
    assert get_transport_route_phrase(nutshell) == "Norway in a Nutshell to Bergen"


def test_patch_bu_without_explicit_title_uses_complete_route_endpoint_not_first_leg() -> None:
    source = "Norway in a Nutshell - Includes: Fjord Cruise Flåm to Gudvangen, Coach Transfer Gudvangen to Voss, Train transfer Voss to Bergen"

    assert extract_norway_nutshell_route_points(source) == ["Flåm", "Gudvangen", "Voss", "Bergen"]
    assert _route_label_from_activity_text(source) == "Norway in a Nutshell to Bergen"

    row = {"type": "Activity", "effective_type": "Activity", "title": "Norway in a Nutshell", "details": source}
    assert get_transport_route_phrase(row) == "Norway in a Nutshell to Bergen"


def test_patch_bu_geilo_is_known_nutshell_route_place() -> None:
    source = "Norway in a Nutshell from Geilo to Bergen - Includes: Train Geilo to Myrdal, Flåm Railway Myrdal to Flåm, Fjord Cruise Flåm to Gudvangen, Coach Gudvangen to Voss, Train Voss to Bergen"

    assert "Geilo" in extract_norway_nutshell_route_points(source)
    assert _route_label_from_activity_text(source) == "Norway in a Nutshell from Geilo to Bergen"


def test_patch_bu_fjordtours_nutshell_addon_catalogue_has_official_core_fields() -> None:
    by_id = {entry.rule_id: entry for entry in FJORDTOURS_NUTSHELL_ADDON_ACTIVITIES}

    assert by_id["flam_stegastein_electric_minibus"].duration == "1 hr 30 min"
    assert by_id["gudvangen_half_day_kayak"].location == "Gudvangen"
    assert by_id["voss_gondola"].season == "7 January - 18 October"
    assert fjordtours_activity_description("bergen_cornelius_dinner_cruise")


def test_patch_bu_fjordtours_addon_matching_uses_curated_titles_and_descriptions() -> None:
    row = {
        "city": "Flåm",
        "title": "Stegastein Viewpoint tour",
        "original_title": "Electric minibus to Stegastein",
        "details": "Flåm: Electric minibus to Stegastein viewpoint - Duration: 1 hr 30 min",
    }

    product = fingerprint_activity(row)
    assert product is not None
    assert product.canonical_family == "flam_stegastein_electric_minibus"
    assert product.display_title == "Electric Minibus to Stegastein Viewpoint"

    match = find_product_match(row)
    assert match is not None
    assert match.description
    assert "Aurlandsfjord" in match.description


def test_patch_bu_fjordtours_addon_catalogue_matches_key_activities() -> None:
    samples = {
        "Local food tasting in Flåm": "flam_local_food_tasting",
        "Half-day kayak tour in Gudvangen": "gudvangen_half_day_kayak",
        "Fjord cruise and dinner at Cornelius": "bergen_cornelius_dinner_cruise",
        "Guided kayak trip in Bergen": "bergen_guided_kayak_trip",
    }

    for title, rule_id in samples.items():
        row = {"city": "Bergen", "title": title, "original_title": title, "details": title}
        product = fingerprint_activity(row)
        assert product is not None, title
        assert product.canonical_family == rule_id
