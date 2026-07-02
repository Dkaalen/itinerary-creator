from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from app_modules.performance_telemetry import measure_timing
from itinerary_generation.common import get_row_type


def parse_and_normalize_itinerary(raw_text, *, state=None):
    """Parse raw input and always run the post-parser normalizer.

    The normalizer is where row-level client-facing fixes are finalized. This
    includes the requested rule: single start time + duration becomes a visible
    start-end range in the day-by-day itinerary.
    """
    with measure_timing(state, "parse_input"):
        parsed_rows = parse_itinerary(raw_text)
    with measure_timing(state, "normalize_rows", count=len(parsed_rows or [])):
        return normalize_itinerary_rows(parsed_rows)


def get_duplicate_count(raw_text_value, parsed_rows=None):
    raw_rows = [
        line for line in raw_text_value.splitlines()
        if "day " in line.strip().lower()
    ]

    parsed_count = len(parsed_rows) if parsed_rows is not None else len(parse_itinerary(raw_text_value))

    return max(len(raw_rows) - parsed_count, 0)


def get_overflow_warnings(grouped_days):
    warnings = []

    for day, rows in grouped_days.items():
        activity_count = sum(1 for row in rows if get_row_type(row) == "Activity")
        block_count = len(rows)
        long_text_score = sum(len(str(row.get("title", ""))) for row in rows)

        if block_count >= 7 or activity_count >= 3 or long_text_score > 520:
            warnings.append(f"{day} may be too full for one A4 page. Review the editable output before exporting.")

    return warnings
