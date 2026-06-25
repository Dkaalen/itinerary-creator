"""Hotel stay-duration normalization."""

from datetime import datetime


def hotel_nights_from_date_range(start_value: object, end_value: object) -> str:
    formats = ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y", "%d.%m.%y")

    def parse(value):
        text = str(value or "").strip()
        for fmt in formats:
            try: return datetime.strptime(text, fmt).date()
            except ValueError: continue
        return None

    start, end = parse(start_value), parse(end_value)
    if not start or not end: return ""
    nights = (end - start).days
    return str(nights) if 0 < nights <= 60 else ""
