from itinerary_generation.date_formatting import (
    format_client_date,
    format_client_date_range,
    ordinal_day,
    parse_date,
)


def test_ordinal_day_suffixes():
    assert ordinal_day(1) == "1st"
    assert ordinal_day(2) == "2nd"
    assert ordinal_day(3) == "3rd"
    assert ordinal_day(4) == "4th"
    assert ordinal_day(11) == "11th"
    assert ordinal_day(12) == "12th"
    assert ordinal_day(13) == "13th"
    assert ordinal_day(21) == "21st"
    assert ordinal_day(22) == "22nd"
    assert ordinal_day(23) == "23rd"


def test_parse_date_accepts_common_input_formats():
    assert parse_date("2026-01-01").isoformat() == "2026-01-01"
    assert parse_date("01/01/2026").isoformat() == "2026-01-01"
    assert parse_date("01.01.2026").isoformat() == "2026-01-01"
    assert parse_date("1 January 2026").isoformat() == "2026-01-01"


def test_format_client_date():
    assert format_client_date("2026-01-01") == "1st of January"
    assert format_client_date("2026-01-02") == "2nd of January"
    assert format_client_date("2026-01-03") == "3rd of January"
    assert format_client_date("2026-01-11") == "11th of January"


def test_format_client_date_range():
    assert format_client_date_range("2026-01-01", "2026-01-06") == "1st of January - 6th of January"
    assert format_client_date_range("2026-01-01", "") == "1st of January"
    assert format_client_date_range("", "2026-01-06") == "6th of January"
    assert format_client_date_range("2026-01-01", "2026-01-01") == "1st of January"
