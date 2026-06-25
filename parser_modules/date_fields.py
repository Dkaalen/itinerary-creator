"""Date-field parsing helpers for itinerary parser rows."""

import re
from datetime import datetime, timedelta

from parser_modules.common import clean_space


def excel_serial_date(value):
    """Return True for Excel serial dates commonly pasted from calculator rows."""

    text = clean_space(value)
    return bool(re.fullmatch(r"4\d{4}(?:\.0)?", text))


def parse_itinerary_date(value):
    text = clean_space(value)
    if not text:
        return None
    if excel_serial_date(text):
        try:
            return datetime(1899, 12, 30) + timedelta(days=int(float(text)))
        except Exception:
            return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def date_derived_hotel_nights(start_date, end_date):
    start = parse_itinerary_date(start_date)
    end = parse_itinerary_date(end_date)
    if not start or not end:
        return ""
    nights = (end.date() - start.date()).days
    if 0 < nights <= 60:
        return str(nights)
    return ""


# Backwards-compatible aliases for tests or legacy imports.
_excel_serial_date = excel_serial_date
_parse_itinerary_date = parse_itinerary_date
_date_derived_hotel_nights = date_derived_hotel_nights
