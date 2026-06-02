from itinerary_generation.health_report import build_itinerary_health_report, format_itinerary_health_report
from itinerary_generation.quality_gate import evaluate_itinerary_quality


def test_health_report_summarizes_day_coverage_route_and_row_statuses():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Helsinki", "commercial_status": "included"},
        {"day": "Day 2", "type": "Activity", "effective_type": "Activity", "city": "Rovaniemi", "commercial_status": "included"},
        {"day": "Day 3", "type": "Transfer", "effective_type": "Transfer", "city": "Tromsø", "commercial_status": "self_arranged"},
        {"day": "Day 4", "type": "Flight", "effective_type": "Flight", "city": "Bergen", "commercial_status": "excluded"},
        {
            "day": "Day 5",
            "type": "Optional",
            "effective_type": "Activity",
            "city": "Oslo",
            "commercial_status": "optional",
            "is_optional": True,
        },
    ]

    report = build_itinerary_health_report(rows)

    assert report.input_days == 5
    assert report.generated_days == 4
    assert report.included_rows == 2
    assert report.optional_rows == 1
    assert report.self_arranged_rows == 1
    assert report.excluded_rows == 1
    assert report.hotels_found == 1
    assert report.activities_found == 1
    assert report.transfers_found == 2
    assert report.route == ("Helsinki", "Rovaniemi", "Tromsø")

    text = format_itinerary_health_report(report)
    assert "Itinerary Health Report" in text
    assert "Input days: 5" in text
    assert "Generated days: 4" in text
    assert "Route: Helsinki → Rovaniemi → Tromsø" in text
    assert "Warnings:" in text


def test_health_report_is_clear_when_validation_has_no_issues():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo", "commercial_status": "included"},
        {"day": "Day 2", "type": "Activity", "effective_type": "Activity", "city": "Bergen", "commercial_status": "included"},
    ]

    report = build_itinerary_health_report(rows, validation_report=evaluate_itinerary_quality(rows))

    assert report.status == "Clear"
    assert report.warnings == ()
    assert "Warnings: none" in format_itinerary_health_report(report)


def test_health_report_surfaces_validation_and_parser_diagnostics():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Helsinki", "commercial_status": "included"},
        {
            "day": "Day 8",
            "type": "Optional",
            "effective_type": "Activity",
            "city": "Oslo",
            "commercial_status": "optional",
            "is_optional": True,
        },
    ]

    report = build_itinerary_health_report(
        rows,
        validation_report=evaluate_itinerary_quality(rows),
        parser_diagnostics=[{"category": "possible_typo", "message": "demo", "raw": "demo"}],
    )

    assert report.status == "Needs review"
    assert any("Input reaches Day 8" in warning for warning in report.warnings)
    assert any("Parser diagnostics recorded: 1 notice" in warning for warning in report.warnings)
