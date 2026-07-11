from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from scripts.real_excel_fixture_bank import build_candidate_index
from scripts.real_output_qa.rendering import render_candidate


def test_drive_row_keeps_route_identity_and_does_not_turn_duration_into_clock_time():
    rows = normalize_itinerary_rows(
        parse_itinerary(
            "Day 1\tDrive\tSnæfellsnes: Drive to Reykjavík - Driving time: 2.5hrs - 3.5hrs - Highlights: Kirkjufell"
        )
    )

    drive = rows[0]
    assert drive["title"] == "Drive to Reykjavík"
    assert drive["time"] == ""
    assert drive["route_origin"] == "Snæfellsnes"
    assert drive["route_destination"] == "Reykjavík"


def test_real_self_drive_return_day_uses_route_truth_instead_of_admin_fallback():
    candidate = next(
        item for item in build_candidate_index()
        if item.fixture_id == "Standard-Itinerary-Iceland.xlsx::10D SD"
    )
    result = render_candidate(candidate)
    day9 = next(day for day in result.context.render_document.days if int(day.number) == 9)
    drive = next(row for row in result.rows if row.get("day") == "Day 9" and row.get("type") == "Drive")

    assert (drive["route_origin"], drive["route_destination"]) == ("Snæfellsnes", "Reykjavík")
    assert day9.title == "Return to Reykjavík"
    assert "the day’s arrangements are listed below" not in day9.intro.lower()
    travel_lines = [line for block in day9.blocks if block.kind == "travel_sequence" for line in block.lines]
    assert any("Snæfellsnes to Reykjavík" in line for line in travel_lines)


def test_real_self_drive_route_days_are_not_reclassified_as_country_arrivals():
    candidate = next(
        item for item in build_candidate_index()
        if item.fixture_id == "Standard-Itinerary-Iceland.xlsx::10D SD"
    )
    result = render_candidate(candidate)
    day2 = next(day for day in result.context.render_document.days if int(day.number) == 2)

    assert day2.title == "Drive to Vík"
    assert "Drive from Reykjavík to Vík" in day2.intro
    assert "by travel" not in day2.intro


def test_real_self_drive_departure_does_not_claim_an_arranged_transfer():
    candidate = next(
        item for item in build_candidate_index()
        if item.fixture_id == "Standard-Itinerary-Iceland.xlsx::10D SD"
    )
    result = render_candidate(candidate)
    day10 = next(day for day in result.context.render_document.days if int(day.number) == 10)

    assert "drive to" in day10.intro.lower()
    assert "rental vehicle" in day10.intro.lower()
    assert "arranged transfer" not in day10.intro.lower()


def test_real_self_drive_return_without_activity_does_not_claim_listed_activities():
    candidate = next(
        item for item in build_candidate_index()
        if item.fixture_id == "Standard-Itinerary-Iceland.xlsx::10D SD"
    )
    result = render_candidate(candidate)
    day9 = next(day for day in result.context.render_document.days if int(day.number) == 9)

    assert "listed activities" not in day9.intro.lower()
    assert day9.intro.startswith("Drive from Snæfellsnes back to Reykjavík")
    assert "arrangements are listed below" not in day9.intro.lower()
