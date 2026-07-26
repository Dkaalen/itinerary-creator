from __future__ import annotations

from collections import Counter
from pathlib import Path
from tests.support.static_contracts import read_contract_text

from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows

from itinerary_generation.group_tour_domain import (
    group_tour_day_from_row,
    group_tour_package_from_row,
)
from itinerary_generation.reference_corpus import iceland_reference_payload


REPO_ROOT = Path(__file__).resolve().parents[1]


def _sheet(name: str) -> dict:
    return next(item for item in iceland_reference_payload()["sheets"] if item["sheet_name"] == name)


def _integrated_sheet(name: str) -> list[dict]:
    sheet = _sheet(name)
    return normalize_itinerary_rows(
        sheet["rows"],
        source_name=sheet["sheet_name"],
        group_tour_season=sheet["season"],
    )


def _package(rows: list[dict]):
    packages = [group_tour_package_from_row(row) for row in rows]
    packages = [package for package in packages if package is not None]
    assert len(packages) == 1
    return packages[0]


def test_all_gts_and_gtw_sheets_integrate_one_package_with_ordered_days() -> None:
    for code, season in (("GTS", "summer"), ("GTW", "winter")):
        for itinerary_days in (5, 6, 7, 8, 10):
            name = f"{itinerary_days}D {code}"
            rows = _integrated_sheet(name)
            package = _package(rows)
            expected_package_days = itinerary_days - 2

            assert package.season == season
            assert package.duration_days == expected_package_days
            assert package.itinerary_start_day == 2
            assert package.itinerary_end_day == itinerary_days - 1
            assert [day.package_day_number for day in package.day_segments] == list(
                range(1, expected_package_days + 1)
            )
            assert [day.itinerary_day_number for day in package.day_segments] == list(
                range(2, itinerary_days)
            )

            masters = [row for row in rows if row.get("group_tour_role") == "package_master"]
            segments = [row for row in rows if row.get("group_tour_role") == "day_segment"]
            assert len(masters) == 1
            assert len(segments) == expected_package_days
            assert all(row["group_tour_package_id"] == package.package_id for row in segments)
            assert all(row["group_tour_season"] == season for row in segments)
            assert not any(str(row.get("id") or "").casefold() == "totals" for row in rows)


def test_parser_accepts_explicit_group_tour_and_commercial_row_types() -> None:
    source = """Day 2\tActivity\tReykjavik: 3-Day Winter Minibus Tour - Time: 8:00 am - Meeting point: Hotel pick-up - Includes: Guide, 2 nights hotel accommodation
Day 2\tGroup Tour\tReykjavik: Day 1: Golden Circle - Visit Thingvellir and stay in a countryside hotel with breakfast.
Day 3\tGroup Tour\tReykjavik: Day 2: South Coast - Visit waterfalls and stay in a countryside hotel with breakfast.
Day 4\tGroup Tour\tReykjavik: Day 3: Glacier Lagoon - Return to Reykjavik.
Day 2\tActivity Upgrade\tReykjavik: Optional Blue Lagoon admission
Day 2\tSingle Supplement Fee\tReykjavik: Mandatory for solo travelers
"""
    parsed = parse_itinerary(source)
    assert [row["type"] for row in parsed] == [
        "Activity",
        "Group Tour",
        "Group Tour",
        "Group Tour",
        "Activity Upgrade",
        "Single Supplement Fee",
    ]
    assert parsed[-2]["commercial_status"] == "optional"
    assert parsed[-1]["commercial_status"] == "optional"

    rows = normalize_itinerary_rows(
        parsed,
        source_name="embedded-city-example",
        group_tour_season="winter",
    )
    package = _package(rows)
    segments = [group_tour_day_from_row(row) for row in rows]
    segments = [segment for segment in segments if segment is not None]

    assert package.title == "3-Day Winter Minibus Tour"
    assert [segment.title for segment in segments] == ["Golden Circle", "South Coast", "Glacier Lagoon"]
    assert [segment.itinerary_day_number for segment in segments] == [2, 3, 4]
    assert all(row.get("effective_type") != "Activity" for row in rows if row.get("type") == "Group Tour")


def test_commercial_rows_are_related_but_never_merged_into_package_days() -> None:
    rows = _integrated_sheet("10D GTS")
    package = _package(rows)
    commercial = [row for row in rows if row.get("group_tour_role") == "commercial_item"]
    independent_hotels = [row for row in rows if row.get("type") == "Hotel"]

    assert Counter(row["group_tour_commercial_category"] for row in commercial) == {
        "transfer_package": 4,
        "activity_upgrade": 5,
        "single_supplement": 1,
        "extra_hotel_night": 1,
    }
    assert all(row["related_group_tour_package_id"] == package.package_id for row in commercial)
    assert all(row["commercial_status"] == "optional" for row in commercial)
    assert all(row["is_optional"] is True for row in commercial)
    assert all("group_tour_package_id" not in row for row in commercial)
    assert all("related_group_tour_package_id" not in row for row in independent_hotels)
    assert all(row.get("group_tour_role") is None for row in independent_hotels)


def test_explicitly_selected_commercial_upgrade_is_not_left_optional() -> None:
    sheet = _sheet("5D GTS")
    source_rows = [dict(row) for row in sheet["rows"]]
    selected = next(row for row in source_rows if row.get("type") == "Activity Upgrade")
    selected["units"] = "1"
    selected["commercial_status"] = "included"

    rows = normalize_itinerary_rows(
        source_rows,
        source_name="5D GTS selected upgrade",
        group_tour_season="summer",
    )
    upgrade = next(
        row
        for row in rows
        if row.get("group_tour_role") == "commercial_item"
        and row.get("travel_element") == selected.get("travel_element")
    )

    assert upgrade["group_tour_commercial_selected"] is True
    assert upgrade["commercial_status"] == "included"
    assert upgrade["commercial_reason"] == "group_tour_commercial_add_on_selected"
    assert upgrade["is_optional"] is False


def test_package_day_source_text_and_supplier_order_are_preserved() -> None:
    sheet = _sheet("5D GTW")
    source_days = [row for row in sheet["rows"] if row.get("type") == "Group Tour"]
    rows = _integrated_sheet("5D GTW")
    package = _package(rows)

    assert [day.source_text for day in package.day_segments] == [row["travel_element"] for row in source_days]
    assert [day.package_day_number for day in package.day_segments] == [1, 2, 3]
    assert "subject to weather and road conditions" in package.day_segments[-1].source_text
    assert any(
        "subject to weather and road conditions" in item.casefold()
        for item in package.day_segments[-1].conditional_items
    )


def test_sheet_season_metadata_wins_and_conflict_remains_visible() -> None:
    package = _package(_integrated_sheet("7D GTS"))

    assert package.season == "summer"
    assert "Winter Minibus Tour" in package.title
    assert "group_tour_season_source_conflict" in package.warnings


def test_pre_and_post_tour_services_remain_independent_rows() -> None:
    rows = _integrated_sheet("6D GTW")
    package = _package(rows)
    hotels = [row for row in rows if row.get("type") == "Hotel"]
    transfers = [row for row in rows if row.get("type") == "Transfer"]

    assert len(hotels) == 2
    assert len(transfers) == 2
    for row in hotels + transfers:
        assert row.get("group_tour_role") is None
        assert "group_tour_package_id" not in row
        assert "related_group_tour_package_id" not in row
    assert package.accommodation_policy.included is True


def test_real_group_tour_fixture_is_annotated_automatically() -> None:
    fixture_text = (REPO_ROOT / "tests" / "fixtures" / "real_inputs" / "iceland_group_tour_winter.txt").read_text(
        encoding="utf-8"
    )
    rows = normalize_itinerary_rows(parse_itinerary(fixture_text))
    package = _package(rows)

    assert package.duration_days == 5
    assert package.itinerary_start_day == 2
    assert package.itinerary_end_day == 6
    assert package.commercial_status == "included"
    assert [row.get("group_tour_role") for row in rows].count("package_master") == 1
    assert [row.get("group_tour_role") for row in rows].count("day_segment") == 5


def test_ordinary_guided_activities_are_not_linked_into_a_package() -> None:
    source = """Day 1\tActivity\tReykjavik: Golden Circle Tour - Time: 9:00 am - 5:00 pm
Day 2\tActivity\tReykjavik: South Coast Tour - Time: 9:00 am - 7:00 pm
"""
    rows = normalize_itinerary_rows(parse_itinerary(source))

    assert all(row.get("group_tour_role") is None for row in rows)
    assert all(group_tour_package_from_row(row) is None for row in rows)


def test_runtime_integration_does_not_import_reference_corpus() -> None:
    parsing_source = read_contract_text(REPO_ROOT / "itinerary_domain" / "group_tour_parsing.py")

    assert "reference_corpus" not in parsing_source
