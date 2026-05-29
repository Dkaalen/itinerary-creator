from itinerary_generation.date_resolver import get_day_date_text, get_trip_date_range_text


def test_get_day_date_text_uses_first_available_row_date():
    rows = [
        {"start_date": "", "end_date": ""},
        {"start_date": "2026-01-01", "end_date": ""},
    ]

    assert get_day_date_text(rows) == "1st of January"


def test_get_day_date_text_supports_day_range():
    rows = [{"start_date": "2026-01-01", "end_date": "2026-01-02"}]

    assert get_day_date_text(rows) == "1st of January - 2nd of January"


def test_get_trip_date_range_text_uses_earliest_start_and_latest_end():
    rows = [
        {"start_date": "2026-01-03", "end_date": "2026-01-04"},
        {"start_date": "2026-01-01", "end_date": "2026-01-02"},
        {"start_date": "2026-01-06", "end_date": ""},
    ]

    assert get_trip_date_range_text(rows) == "1st of January - 6th of January"


def test_get_trip_date_range_text_returns_blank_without_dates():
    assert get_trip_date_range_text([{"start_date": "", "end_date": ""}]) == ""
