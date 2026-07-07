from __future__ import annotations

from collections import Counter

from itinerary_generation.reference_corpus import (
    CORPUS_VERSION,
    blocking_reference_corpus_issues,
    clean_activity_references,
    destination_capability_map,
    iceland_reference_payload,
    reference_corpus_manifest,
    reference_corpus_summary,
    standard_input_templates,
    unresolved_placeholders,
    validate_reference_corpus,
)


def _sheet(name: str) -> dict:
    return next(sheet for sheet in iceland_reference_payload()["sheets"] if sheet["sheet_name"] == name)


def _type_counts(sheet: dict) -> Counter[str]:
    return Counter(row.get("type", "") for row in sheet["rows"])


def test_reference_corpus_is_versioned_and_complete() -> None:
    summary = reference_corpus_summary()

    assert summary.version == CORPUS_VERSION == "ih1-v1"
    assert summary.standard_template_count == 643
    assert len({item.canonical_destination for item in standard_input_templates()}) == 100
    assert summary.clean_activity_count == 163
    assert len({item.canonical_city for item in clean_activity_references()}) == 15
    assert summary.iceland_sheet_count == 15
    assert summary.iceland_row_count == 402
    assert summary.blocking_issue_count == 0


def test_reference_manifest_checksums_and_schema_are_valid() -> None:
    manifest = reference_corpus_manifest()

    assert manifest["schema_version"] == 1
    assert manifest["corpus_version"] == CORPUS_VERSION
    assert manifest["iceland_sheet_count"] == 15
    assert {item["name"] for item in manifest["files"]} == {
        "standard_input_templates.tsv",
        "clean_activity_inputs.tsv",
        "iceland_standard_itinerary.json",
    }
    assert blocking_reference_corpus_issues() == ()


def test_standard_templates_define_destination_capabilities_without_guessing() -> None:
    capabilities = destination_capability_map()

    assert len(standard_input_templates()) == 643
    assert capabilities["Oslo"] == {
        "Hotel",
        "Leisure",
        "Transfer",
        "Flight",
        "Cruise",
        "Train",
        "Coach",
    }
    assert capabilities["Flåm"] == {"Hotel", "Leisure", "Transfer", "Cruise", "Train", "Coach"}
    assert capabilities["Longyearbyen"] == {"Hotel", "Leisure", "Transfer", "Flight"}
    assert "Train" not in capabilities["Longyearbyen"]


def test_standard_placeholders_are_explicit_and_do_not_become_client_facts() -> None:
    hotel = next(
        item
        for item in standard_input_templates()
        if item.service_type == "Hotel" and item.canonical_destination == "Oslo"
    )

    assert hotel.placeholders == ("BedType", "HotelName", "MealPlan", "RoomCategory", "X")
    assert set(unresolved_placeholders(hotel.template_text)) == set(hotel.placeholders)
    assert unresolved_placeholders("Oslo: Check in to Hotel Continental for 2 nights") == ()
    assert unresolved_placeholders("Stay at [HotelName] for [X] nights") == ("HotelName", "X")


def test_clean_activity_corpus_preserves_conditional_commercial_language() -> None:
    entries = clean_activity_references()
    conditional = {entry.record_id: entry for entry in entries if entry.conditional_markers}

    assert len(conditional) == 10
    assert any("if snow" in entry.conditional_markers for entry in entries)
    assert any("weather permitting" in entry.conditional_markers for entry in entries)
    assert any("not guaranteed" in entry.conditional_markers for entry in entries)
    assert any("upon request" in entry.conditional_markers for entry in entries)


def test_clean_activity_validator_surfaces_known_source_quality_findings() -> None:
    issues = validate_reference_corpus()
    codes = Counter(issue.code for issue in issues)

    assert codes == {
        "activity_location_differs_from_catalogue_city": 3,
        "suspicious_activity_time_range": 2,
        "ambiguous_activity_time_options": 1,
        "activity_missing_time_label": 1,
        "duplicate_clean_activity": 1,
        "malformed_activity_time_spacing": 1,
        "group_tour_master_missing_season": 1,
    }
    assert all(issue.severity == "warning" for issue in issues)
    assert any(issue.message == "Helsinki -> Tallinn" for issue in issues)
    assert any("7:30 pm - 12:30 pm" in issue.message for issue in issues)
    assert any("10: 50 am" in issue.message for issue in issues)


def test_iceland_reference_contains_only_sd_gts_and_gtw_sheets() -> None:
    payload = iceland_reference_payload()
    names = {sheet["sheet_name"] for sheet in payload["sheets"]}

    assert payload["source"]["included_sheet_codes"] == ["SD", "GTS", "GTW"]
    assert payload["source"]["excluded_sheet_codes"] == ["RS", "RW", "Kalk"]
    assert names == {
        *(f"{days}D SD" for days in (5, 6, 7, 8, 10)),
        *(f"{days}D GTS" for days in (5, 6, 7, 8, 10)),
        *(f"{days}D GTW" for days in (5, 6, 7, 8, 10)),
    }


def test_self_drive_reference_keeps_one_drive_row_per_itinerary_day() -> None:
    for days in (5, 6, 7, 8, 10):
        sheet = _sheet(f"{days}D SD")
        counts = _type_counts(sheet)

        assert sheet["itinerary_kind"] == "self_drive"
        assert counts["Drive"] == days
        assert counts["Group Tour"] == 0
        assert counts["Car"] == 2
        assert counts["Activity Upgrade"] >= 4


def test_group_tour_reference_keeps_one_master_and_ordered_package_days() -> None:
    for code, season in (("GTS", "summer"), ("GTW", "winter")):
        for days in (5, 6, 7, 8, 10):
            sheet = _sheet(f"{days}D {code}")
            counts = _type_counts(sheet)
            group_rows = [row for row in sheet["rows"] if row.get("type") == "Group Tour"]

            assert sheet["itinerary_kind"] == "group_tour"
            assert sheet["season"] == season
            assert counts["Activity"] == 1
            assert counts["Group Tour"] == days - 2
            assert [row["day"] for row in group_rows] == [f"Day {number}" for number in range(2, days)]
            assert [row["travel_element"].split()[1].rstrip(":-") for row in group_rows] == [
                str(number) for number in range(1, days - 1)
            ]


def test_group_tour_reference_retains_optional_and_commercial_rows_separately() -> None:
    summer = _type_counts(_sheet("10D GTS"))
    winter = _type_counts(_sheet("10D GTW"))

    for counts in (summer, winter):
        assert counts["Transfer package"] == 4
        assert counts["Activity Upgrade"] == 5
        assert counts["Single Supplement Fee"] == 1
        assert counts["Extra Hotel Night"] == 1
