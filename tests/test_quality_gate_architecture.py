from itinerary_generation.quality_gate import (
    build_quality_snapshot,
    evaluate_itinerary_quality,
    validate_itinerary_integrity,
)


def test_quality_snapshot_counts_statuses_and_days():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo"},
        {"day": "Day 2", "type": "Activity", "effective_type": "Activity", "city": "Oslo"},
        {
            "day": "Day 3",
            "type": "Optional",
            "effective_type": "Activity",
            "city": "Oslo",
            "is_optional": True,
            "commercial_status": "optional",
        },
        {
            "day": "Day 4",
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Oslo",
            "commercial_status": "self_arranged",
        },
    ]

    snapshot = build_quality_snapshot(rows)

    assert snapshot.row_count == 4
    assert snapshot.important_count == 4
    assert snapshot.main_count == 3
    assert snapshot.optional_count == 1
    assert snapshot.self_arranged_count == 1
    assert snapshot.input_max_day == 4
    assert snapshot.main_max_day == 4
    assert snapshot.optional_max_day == 3
    assert snapshot.input_cities == ("Oslo",)


def test_quality_gate_blocks_late_optional_leak():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Helsinki"},
        {"day": "Day 5", "type": "Activity", "effective_type": "Activity", "city": "Rovaniemi"},
        {
            "day": "Day 6",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Rovaniemi",
            "is_optional": True,
            "commercial_status": "optional",
        },
        {
            "day": "Day 13",
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Oslo",
            "is_optional": True,
            "commercial_status": "optional",
        },
    ]

    report = evaluate_itinerary_quality(rows)

    assert report.is_blocked
    assert any(issue.code == "main_itinerary_truncated_by_optional_rows" for issue in report.blocking_issues)
    assert validate_itinerary_integrity(rows) == list(report.issues)


def test_quality_gate_warns_for_large_optional_share_without_blocking_when_main_reaches_end():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo"},
        {"day": "Day 2", "type": "Activity", "effective_type": "Activity", "city": "Oslo"},
        {"day": "Day 3", "type": "Activity", "effective_type": "Activity", "city": "Bergen", "is_optional": True, "commercial_status": "optional"},
        {"day": "Day 4", "type": "Activity", "effective_type": "Activity", "city": "Bergen", "is_optional": True, "commercial_status": "optional"},
        {"day": "Day 5", "type": "Activity", "effective_type": "Activity", "city": "Tromsø", "is_optional": True, "commercial_status": "optional"},
        {"day": "Day 6", "type": "Activity", "effective_type": "Activity", "city": "Tromsø", "is_optional": True, "commercial_status": "optional"},
        {"day": "Day 6", "type": "Departure", "effective_type": "Departure", "city": "Tromsø"},
    ]

    report = evaluate_itinerary_quality(rows)

    assert not report.is_blocked
    assert any(issue.code == "large_optional_share" for issue in report.warnings)
