from pathlib import Path

from itinerary_generation.itinerary_continuity import evaluate_itinerary_continuity
from itinerary_generation.quality_gate import evaluate_client_output_quality, evaluate_itinerary_quality
from itinerary_generation.render_model import RenderDocument
from itinerary_generation.structured_builder import build_itinerary_document


def _codes(rows):
    return {finding.code for finding in evaluate_itinerary_continuity(rows)}


def _hotel(day: str, city: str, row_id: str):
    return {
        "day": day,
        "type": "Hotel",
        "effective_type": "Hotel",
        "city": city,
        "title": f"Hotel stay in {city}",
        "row_id": row_id,
    }


def _activity(day: str, city: str, title: str, time: str, row_id: str, **extra):
    return {
        "day": day,
        "type": "Activity",
        "effective_type": "Activity",
        "city": city,
        "title": title,
        "time": time,
        "row_id": row_id,
        **extra,
    }


def _train(day: str, origin: str, destination: str, row_id: str, *, self_arranged: bool = False):
    status = "self_arranged" if self_arranged else "included"
    title = f"{'Self-arranged ' if self_arranged else ''}train from {origin} to {destination}"
    return {
        "day": day,
        "type": "Train",
        "effective_type": "Train",
        "city": origin,
        "title": title,
        "details": f"{origin} to {destination}",
        "commercial_status": status,
        "row_id": row_id,
    }


def test_exact_activity_overlap_blocks_generation():
    rows = [
        _activity("Day 2", "Oslo", "Essential walking tour", "10:00 AM - 12:00 PM", "a1"),
        _activity("Day 2", "Oslo", "Oslofjord cruise", "11:00 AM - 1:00 PM", "a2"),
    ]

    report = evaluate_itinerary_quality(rows)

    assert report.is_blocked
    issue = next(issue for issue in report.blocking_issues if issue.code == "overlapping_arranged_activities")
    assert "Essential walking tour" in issue.context
    assert "Oslofjord cruise" in issue.context


def test_adjacent_activity_times_do_not_overlap():
    rows = [
        _activity("Day 2", "Copenhagen", "Walking tour", "9:00 AM - 12:00 PM", "a1"),
        _activity("Day 2", "Copenhagen", "Museum visit", "12:00 PM - 2:00 PM", "a2"),
    ]

    assert "overlapping_arranged_activities" not in _codes(rows)


def test_optional_overlap_does_not_block_included_itinerary():
    rows = [
        _activity("Day 2", "Oslo", "Included tour", "10:00 AM - 12:00 PM", "a1"),
        _activity(
            "Day 2",
            "Oslo",
            "Optional cruise",
            "11:00 AM - 1:00 PM",
            "a2",
            is_optional=True,
            commercial_status="optional",
        ),
    ]

    assert "overlapping_arranged_activities" not in _codes(rows)


def test_alternative_departure_options_are_not_treated_as_parallel_commitments():
    rows = [
        _activity("Day 2", "Helsinki", "Sauna admission", "10:00 AM - 12:00 PM / 2:00 PM - 4:00 PM", "a1"),
        _activity("Day 2", "Helsinki", "Walking tour", "11:00 AM - 1:00 PM", "a2"),
    ]

    assert "overlapping_arranged_activities" not in _codes(rows)


def test_destination_jump_without_travel_leg_blocks_generation():
    rows = [
        _hotel("Day 1", "Oslo", "h1"),
        _hotel("Day 2", "Bergen", "h2"),
    ]

    report = evaluate_itinerary_quality(rows)

    assert report.is_blocked
    assert "unexplained_destination_jump" in {issue.code for issue in report.blocking_issues}


def test_arranged_route_bridges_accommodation_change():
    rows = [
        _hotel("Day 1", "Oslo", "h1"),
        _train("Day 2", "Oslo", "Bergen", "t1"),
        _hotel("Day 2", "Bergen", "h2"),
    ]

    assert not evaluate_itinerary_quality(rows).is_blocked
    assert not _codes(rows).intersection({"unexplained_destination_jump", "route_origin_discontinuity", "travel_destination_accommodation_mismatch"})


def test_self_arranged_route_is_valid_continuity_evidence():
    rows = [
        _hotel("Day 1", "Oslo", "h1"),
        _train("Day 2", "Oslo", "Bergen", "t1", self_arranged=True),
        _hotel("Day 2", "Bergen", "h2"),
    ]

    assert "unexplained_destination_jump" not in _codes(rows)


def test_route_origin_must_match_established_location():
    rows = [
        _hotel("Day 1", "Oslo", "h1"),
        _train("Day 2", "Bergen", "Flåm", "t1"),
        _hotel("Day 2", "Flåm", "h2"),
    ]

    assert "route_origin_discontinuity" in _codes(rows)


def test_route_destination_must_match_following_hotel():
    rows = [
        _hotel("Day 1", "Oslo", "h1"),
        _train("Day 2", "Oslo", "Bergen", "t1"),
        _hotel("Day 2", "Flåm", "h2"),
    ]

    assert "travel_destination_accommodation_mismatch" in _codes(rows)


def test_activity_excursion_does_not_move_the_overnight_base():
    rows = [
        _hotel("Day 1", "Ålesund", "h1"),
        _activity("Day 2", "Geiranger", "Geirangerfjord day excursion", "8:30 AM - 6:00 PM", "a1"),
        {"day": "Day 3", "type": "Leisure", "effective_type": "Leisure", "city": "Ålesund", "title": "Leisure in Ålesund", "row_id": "l1"},
    ]

    assert not _codes(rows).intersection({"unexplained_destination_jump", "route_origin_discontinuity"})


def test_arrival_in_new_city_without_travel_leg_is_visible_as_warning():
    rows = [
        _hotel("Day 1", "Oslo", "h1"),
        {"day": "Day 2", "type": "Arrival", "effective_type": "Arrival", "city": "Bergen", "title": "Arrival in Bergen", "row_id": "r1"},
        _hotel("Day 2", "Bergen", "h2"),
    ]

    report = evaluate_itinerary_quality(rows)

    assert not report.is_blocked
    assert "arrival_without_travel_leg" in {issue.code for issue in report.warnings}


def test_structured_document_and_late_output_gate_use_same_continuity_contract():
    rows = [
        _activity("Day 2", "Oslo", "Walking tour", "10:00 AM - 12:00 PM", "a1"),
        _activity("Day 2", "Oslo", "Cruise", "11:00 AM - 1:00 PM", "a2"),
    ]

    document = build_itinerary_document(rows)
    structured_codes = {warning.code for warning in document.warnings}
    client_codes = {issue.code for issue in evaluate_client_output_quality(RenderDocument(), source_rows=rows).blocking_issues}

    assert "overlapping_arranged_activities" in structured_codes
    assert "overlapping_arranged_activities" in client_codes


def test_leisure_day_in_new_destination_requires_travel_evidence():
    rows = [
        _hotel("Day 1", "Oslo", "h1"),
        {"day": "Day 2", "type": "Leisure", "effective_type": "Leisure", "city": "Bergen", "title": "Leisure in Bergen", "row_id": "l1"},
    ]

    assert "unexplained_destination_jump" in _codes(rows)


def test_arrival_without_hotel_still_establishes_new_destination_with_warning():
    rows = [
        _hotel("Day 1", "Oslo", "h1"),
        {"day": "Day 2", "type": "Arrival", "effective_type": "Arrival", "city": "Bergen", "title": "Arrival in Bergen", "row_id": "r1"},
        {"day": "Day 3", "type": "Leisure", "effective_type": "Leisure", "city": "Bergen", "title": "Leisure in Bergen", "row_id": "l1"},
    ]

    findings = evaluate_itinerary_continuity(rows)

    assert [finding.code for finding in findings] == ["arrival_without_travel_leg"]


def test_raw_oslo_conflict_is_caught_after_real_parser_and_normalizer():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows

    raw = """
Day 1\tHotel\t01.08.2026\t04.08.2026\t\t\t\t\tOslo\tOslo: Hotel stay - 3 nights
Day 2\tActivity\t02.08.2026\t\t\t\t\t\tOslo\tOslo: Essential walking tour - Time: 10:00 am - 12:00 pm
Day 2\tActivity\t02.08.2026\t\t\t\t\t\tOslo\tOslo: Electric Oslofjord cruise - Time: 11:00 am - 1:00 pm
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))

    assert "overlapping_arranged_activities" in {issue.code for issue in evaluate_itinerary_quality(rows).blocking_issues}


def test_compound_helsinki_excursion_is_not_mistaken_for_route_continuity():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows

    raw = """
Day 1\tHotel\t23.12.2026\t26.12.2026\t\t\t\t\tHelsinki\tHelsinki: Hotel stay - 3 nights
Day 2\tActivity\t24.12.2026\t\t\t\t\t\tHelsinki\tHelsinki: City Highlights & Suomenlinna Day Tour - Time: 10:00 am - 3:00 pm - Includes: Coach sightseeing, professional guide, round-trip ferry to Suomenlinna
Day 3\tLeisure\t25.12.2026\t\t\t\t\t\tHelsinki\tHelsinki: Spend time at leisure
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))

    activity = next(row for row in rows if row.get("day") == "Day 2")
    assert activity.get("effective_type") == "Activity"
    assert not evaluate_itinerary_quality(rows).is_blocked


def test_continuity_policy_has_one_owner_and_shared_consumers():
    repo_root = Path(__file__).resolve().parents[1]
    owner_source = (repo_root / "itinerary_generation" / "itinerary_continuity.py").read_text(encoding="utf-8")
    consumer_paths = (
        repo_root / "itinerary_generation" / "generation_quality_gate.py",
        repo_root / "itinerary_generation" / "structured_builder_core.py",
        repo_root / "itinerary_generation" / "client_quality_truth_checks.py",
    )
    consumer_sources = [path.read_text(encoding="utf-8") for path in consumer_paths]

    policy_codes = (
        "overlapping_arranged_activities",
        "route_origin_discontinuity",
        "travel_destination_accommodation_mismatch",
        "unexplained_destination_jump",
    )
    for code in policy_codes:
        assert code in owner_source
        assert all(code not in source for source in consumer_sources)
    assert all("evaluate_itinerary_continuity(" in source for source in consumer_sources)


def test_true_route_coach_activity_retains_transport_classification():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows

    raw = """
Day 5\tActivity\t14.11.2026\t\t\t\t\t\tRovaniemi\tRovaniemi: Arctic Route Coach Transfer to Tromsø
"""
    row = normalize_itinerary_rows(parse_itinerary(raw))[0]

    assert row.get("effective_type") == "Transport"
    assert row.get("title") == "Coach Transfer to Tromsø"


def test_round_trip_rail_and_fjord_day_tour_does_not_move_overnight_base():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows

    raw = """
Day 1\tHotel\t01.08.2026\t08.08.2026\t\t\t\t\tBergen\tBergen: Hotel stay - 7 nights
Day 5\tActivity\t05.08.2026\t\t\t\t\t\tBergen\tBergen: Norway in a Nutshell Self-Guided Grand Sognefjord & Flåm Railway Day Tour - Time: 8:00 am - 6:00 pm - Includes: Cruise from Bergen to Flåm, Flåm Railway to Myrdal, Bergen Railway from Myrdal to Bergen - Description: Return to Bergen in the evening.
Day 6\tLeisure\t06.08.2026\t\t\t\t\t\tBergen\tBergen: Spend time at leisure
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    activity = next(row for row in rows if row.get("day") == "Day 5")

    assert activity.get("effective_type") == "Activity"
    assert "unexplained_destination_jump" not in _codes(rows)


def test_nutshell_contract_uses_final_destination_not_intermediate_leg():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows

    raw = """
Day 1\tHotel\t12.06.2026\t13.06.2026\t\t\t\t\tFlåm\tFlåm: Hotel stay - 1 night
Day 2\tActivity\t13.06.2026\t\t\t\t\t\tFlåm\tFlåm: Norway in a Nutshell to Bergen - Time: TBD - Route: Fjord Cruise Flåm to Gudvangen, Coach Transfer Gudvangen to Voss, Train transfer Voss to Bergen - Includes: Tickets
Day 2\tHotel\t13.06.2026\t14.06.2026\t\t\t\t\tBergen\tBergen: Hotel stay - 1 night
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))

    assert "travel_destination_accommodation_mismatch" not in _codes(rows)


def test_overnight_cruise_uses_source_city_not_service_name_as_origin():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows

    raw = """
Day 1\tHotel\t01.08.2026\t04.08.2026\t\t\t\t\tHelsinki\tHelsinki: Hotel stay - 3 nights
Day 4\tCruise\t04.08.2026\t05.08.2026\t\t\t\t\tHelsinki\tHelsinki: Overnight cruise to Stockholm - Includes: Interior cabin
Day 5\tHotel\t05.08.2026\t06.08.2026\t\t\t\t\tStockholm\tStockholm: Hotel stay - 1 night
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))

    assert "route_origin_discontinuity" not in _codes(rows)
