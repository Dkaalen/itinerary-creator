from __future__ import annotations

from collections import Counter
from pathlib import Path

from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows

from itinerary_generation.group_tour_domain import (
    GROUP_TOUR_CANONICAL_FAMILY,
    GROUP_TOUR_CONTRACT_KIND,
    GROUP_TOUR_CONTRACT_VERSION,
    GROUP_TOUR_PRODUCT_TYPE,
    GroupTourPackage,
    annotate_group_tour_rows,
    build_group_tour_package,
    group_tour_day_from_row,
    group_tour_package_from_row,
)
from itinerary_generation.reference_corpus import iceland_reference_payload


REPO_ROOT = Path(__file__).resolve().parents[1]


def _sheet(name: str) -> dict:
    return next(item for item in iceland_reference_payload()["sheets"] if item["sheet_name"] == name)


def _package(name: str):
    sheet = _sheet(name)
    package = build_group_tour_package(
        sheet["rows"],
        season=sheet["season"],
        source_name=sheet["sheet_name"],
    )
    assert package is not None
    return package


def _normalized_fixture(name: str) -> list[dict]:
    source = (REPO_ROOT / "tests" / "fixtures" / "real_inputs" / name).read_text(encoding="utf-8")
    return normalize_itinerary_rows(parse_itinerary(source))


def test_ih2_all_iceland_group_sheets_build_one_ordered_package_contract() -> None:
    for code, season in (("GTS", "summer"), ("GTW", "winter")):
        for itinerary_days in (5, 6, 7, 8, 10):
            package = _package(f"{itinerary_days}D {code}")
            expected_package_days = itinerary_days - 2

            assert package.canonical_family == GROUP_TOUR_CANONICAL_FAMILY
            assert package.product_type == GROUP_TOUR_PRODUCT_TYPE
            assert package.season == season
            assert package.duration_days == expected_package_days
            assert package.declared_duration_days == expected_package_days
            assert package.itinerary_start_day == 2
            assert package.itinerary_end_day == itinerary_days - 1
            assert [day.package_day_number for day in package.day_segments] == list(
                range(1, expected_package_days + 1)
            )
            assert [day.itinerary_day_number for day in package.day_segments] == list(
                range(2, itinerary_days)
            )
            assert package.commercial_status == "included"
            assert package.commercial_reason == "group_tour_master_with_package_days"


def test_ih2_sheet_season_wins_without_silently_rewriting_conflicting_source() -> None:
    package = _package("7D GTS")

    assert package.season == "summer"
    assert "Winter Minibus Tour" in package.title
    assert "group_tour_season_source_conflict" in package.warnings

    winter = _package("7D GTW")
    assert winter.season == "winter"
    assert "group_tour_season_source_conflict" not in winter.warnings
    assert package.package_id != winter.package_id


def test_ih2_package_accommodation_policy_preserves_promise_without_inventing_hotels() -> None:
    package = _package("5D GTS")
    policy = package.accommodation_policy

    assert policy.included is True
    assert policy.nights == 2
    assert policy.nights_inferred is True
    assert policy.bathroom == "Private bathroom"
    assert policy.meal_plan == "Breakfast included"
    assert policy.exact_properties_confirmed is False
    assert any("Hotel stays with breakfast and private bathroom" in item for item in policy.source_wording)
    assert "accommodation_nights_inferred_from_package_duration" in policy.warnings


def test_ih2_commercial_rows_are_separate_from_package_days_and_inclusions() -> None:
    package = _package("10D GTS")
    counts = Counter(item.category for item in package.commercial_items)

    assert counts == {
        "transfer_package": 4,
        "activity_upgrade": 5,
        "single_supplement": 1,
        "extra_hotel_night": 1,
    }
    assert all(item.selected is False for item in package.commercial_items)
    assert all(item.optional is True for item in package.commercial_items)
    supplement = next(item for item in package.commercial_items if item.category == "single_supplement")
    assert supplement.mandatory_condition == "Mandatory for solo travelers"
    assert all(day.package_day_number for day in package.day_segments)
    assert not any("Single Supplement Fee" in item for item in package.package_inclusions)


def test_ih2_daily_segments_preserve_optional_and_overnight_facts() -> None:
    summer = _package("8D GTS")
    eastfjords = next(day for day in summer.day_segments if day.package_day_number == 4)

    assert eastfjords.title == "The Eastfjords"
    assert eastfjords.overnight_area == "Egilsstaðir"
    assert "Eastfjords" in eastfjords.route
    assert eastfjords.source_text.startswith("Day 4")

    normalized = _normalized_fixture("iceland_group_tour_summer_ring_road.txt")
    normalized_package = build_group_tour_package(normalized, season="summer", source_name="summer-optional")
    assert normalized_package is not None
    normalized_eastfjords = next(day for day in normalized_package.day_segments if day.package_day_number == 4)
    assert any("optional horseback riding" in item.lower() for item in normalized_eastfjords.optional_items)
    assert any("VÖK Baths" in item for item in normalized_eastfjords.optional_items)

    winter = _package("8D GTW")
    glacier = next(day for day in winter.day_segments if day.package_day_number == 3)
    assert glacier.overnight_area == "Vatnajökull"
    assert "Ice Caving" in glacier.title


def test_ih2_contract_metadata_roundtrip_is_versioned_and_lossless() -> None:
    package = _package("10D GTW")
    metadata = package.as_metadata
    restored = GroupTourPackage.from_metadata(metadata)

    assert metadata["kind"] == GROUP_TOUR_CONTRACT_KIND
    assert metadata["schema_version"] == GROUP_TOUR_CONTRACT_VERSION
    assert restored == package


def test_ih2_normalized_winter_fixture_overrides_false_overview_excluded_status() -> None:
    rows = _normalized_fixture("iceland_group_tour_winter.txt")
    overview = next(row for row in rows if (row.get("effective_type") or row.get("type")) == "Day Overview")
    assert overview["commercial_status"] == "excluded"  # Existing generic-parser defect is characterized.

    package = build_group_tour_package(rows, season="winter", source_name="winter-fixture")
    assert package is not None
    assert package.title == "5-Day Holiday Package Icelandic Winter Minibus Tour"
    assert package.commercial_status == "included"
    assert package.commercial_reason == "group_tour_master_with_package_days"
    assert package.duration_days == 5
    assert [day.itinerary_day_number for day in package.day_segments] == [2, 3, 4, 5, 6]
    assert package.day_segments[0].title == "Explore Borgarfjörður Valley & Waterfalls"
    assert package.source_row_ids[0] == overview["row_id"]


def test_ih2_normalized_summer_fixture_keeps_package_day_offset_and_daily_source() -> None:
    rows = _normalized_fixture("iceland_group_tour_summer_ring_road.txt")
    package = build_group_tour_package(rows, season="summer", source_name="summer-fixture")

    assert package is not None
    assert package.duration_days == 6
    assert package.itinerary_start_day == 2
    assert package.itinerary_end_day == 7
    assert package.day_segments[0].package_day_number == 1
    assert package.day_segments[0].itinerary_day_number == 2
    assert package.day_segments[-1].package_day_number == 6
    assert package.day_segments[-1].itinerary_day_number == 7
    assert package.day_segments[-1].title == "Watch Whales & Return to Reykjavík"
    assert "Hauganes" in package.day_segments[-1].route


def test_ih2_annotation_attaches_contract_only_to_master_and_package_days() -> None:
    sheet = _sheet("5D GTW")
    annotated = annotate_group_tour_rows(
        sheet["rows"],
        season=sheet["season"],
        source_name=sheet["sheet_name"],
    )

    masters = [row for row in annotated if "group_tour_package" in row]
    days = [row for row in annotated if "group_tour_day" in row]
    hotels = [row for row in annotated if row.get("type") == "Hotel"]
    commercial = [
        row
        for row in annotated
        if row.get("type") in {"Transfer package", "Activity Upgrade", "Single Supplement Fee", "Extra Hotel Night"}
    ]

    assert len(masters) == 1
    assert len(days) == 3
    assert all("group_tour_package_id" not in row for row in hotels)
    assert all("group_tour_package_id" not in row for row in commercial)

    restored_package = group_tour_package_from_row(masters[0])
    restored_days = [group_tour_day_from_row(row) for row in days]
    assert restored_package is not None
    assert [day.package_day_number for day in restored_days if day is not None] == [1, 2, 3]


def test_ih2_ordinary_activities_do_not_become_group_tour_packages() -> None:
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Reykjavík",
            "title": "Golden Circle Tour",
            "details": "A guided day tour to Thingvellir, Geysir and Gullfoss.",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Reykjavík",
            "title": "South Coast Tour",
            "details": "A guided day tour to waterfalls and Reynisfjara.",
        },
    ]

    assert build_group_tour_package(rows, season="summer") is None
    assert annotate_group_tour_rows(rows, season="summer") == rows


def test_ih2_runtime_contract_does_not_import_reference_corpus() -> None:
    source = (REPO_ROOT / "itinerary_generation" / "group_tour_domain.py").read_text(encoding="utf-8")

    assert "from itinerary_generation.reference_corpus" not in source
    assert "import itinerary_generation.reference_corpus" not in source
