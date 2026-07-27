from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata

from itinerary_generation.data.nordic_destination_registry import destination_for_alias
from place_alias_data import PLACES
from itinerary_generation.destination_content import travel_day_intro
from itinerary_generation.destination_helpers import clean_client_title, get_display_destination_city
from place_alias_text import _key, normalize_place_key
from shared.text import clean_space
from text_polish import polish_client_text, polish_title


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "text_normalization_snapshots.json"


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_generic_whitespace_snapshot() -> None:
    for case in _fixture()["whitespace"]:
        assert clean_space(case["input"]) == case["expected"]


def test_nordic_place_key_and_registry_snapshot() -> None:
    for case in _fixture()["place_keys"]:
        assert normalize_place_key(case["input"]) == case["expected"]
        assert _key(case["input"]) == case["expected"]
        assert destination_for_alias(case["input"]) is not None



def _legacy_destination_registry_key(value: object) -> str:
    text = str(value or "").strip().lower()
    text = (
        text.replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
        .replace("ä", "a")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ð", "d")
        .replace("þ", "th")
    )
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def test_all_destination_alias_keys_match_the_pre_refactor_contract() -> None:
    values = [
        value
        for place in PLACES
        for value in (place.get("canonical", ""), *(place.get("aliases", ()) or ()))
        if str(value or "").strip()
    ]
    assert values
    for value in values:
        assert normalize_place_key(value) == _legacy_destination_registry_key(value), value

def test_client_text_and_title_snapshots() -> None:
    fixture = _fixture()
    for case in fixture["client_text"]:
        assert polish_client_text(case["input"]) == case["expected"]
    for case in fixture["titles"]:
        assert polish_title(case["input"]) == case["expected"]


def test_destination_specific_snapshots() -> None:
    fixture = _fixture()
    for case in fixture["destination_title_cleanup"]:
        assert clean_client_title(case["input"]) == case["expected"]
    for case in fixture["destination_display"]:
        assert get_display_destination_city(case["input"]) == case["expected"]
    for case in fixture["travel_day_intro"]:
        assert travel_day_intro(case["origin"], case["destination"], case["mode"]) == case["expected"]


def test_generic_text_compaction_has_one_implementation_owner() -> None:
    modules = (
        "itinerary_generation/activity_location_contract.py",
        "itinerary_generation/client_quality_truth_checks.py",
        "itinerary_generation/client_text_decisions.py",
        "itinerary_generation/copy/activity_composition.py",
        "itinerary_generation/copy_decision_contract.py",
        "itinerary_generation/day_city_facts.py",
        "itinerary_generation/day_copy_qa.py",
        "itinerary_generation/day_intro_writer.py",
        "itinerary_generation/day_render_activity_blocks.py",
        "itinerary_generation/day_row_selectors.py",
        "itinerary_generation/day_timeline_events.py",
        "itinerary_generation/health_check_rows.py",
        "itinerary_generation/journey_overview_brain.py",
        "itinerary_generation/journey_overview_evidence.py",
        "itinerary_generation/journey_overview_variation.py",
        "shared/source_text_cleanup.py",
        "itinerary_generation/title_decision_helpers.py",
        "itinerary_generation/transport_safety.py",
        "shared/place_label_policy.py",
    )
    forbidden = (
        're.sub(r"\\s+", " ", str(value or "")',
        '" ".join(str(value or "").split())',
    )
    for relative_path in modules:
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "from shared.text import clean_space" in source, relative_path
        assert not any(pattern in source for pattern in forbidden), relative_path


def test_destination_alias_layers_share_public_place_key_owner() -> None:
    alias_maps = (PROJECT_ROOT / "place_alias_maps.py").read_text(encoding="utf-8")
    alias_queries = (PROJECT_ROOT / "place_alias_queries.py").read_text(encoding="utf-8")
    registry = (PROJECT_ROOT / "itinerary_generation/data/nordic_destination_registry.py").read_text(encoding="utf-8")

    assert "from place_alias_text import normalize_place_key" in alias_maps
    assert "from place_alias_text import normalize_place_key" in alias_queries
    assert "from place_alias_text import normalize_place_key" in registry
    assert "unicodedata.normalize" not in registry
    assert "def _normalise" in registry
