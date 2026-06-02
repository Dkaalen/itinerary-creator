"""Safety validation for itinerary structure before rendering/export.

These checks are intentionally conservative. They catch architecture-level
classification failures, such as normal rows being moved into optional add-ons
and silently truncating the main itinerary.
"""

from __future__ import annotations

from dataclasses import dataclass

from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.row_filters import get_row_type, is_optional_row


@dataclass(frozen=True)
class ItineraryValidationIssue:
    severity: str
    code: str
    message: str


def _max_day(rows) -> int:
    values = [get_day_number(row.get("day", "")) for row in rows or []]
    return max(values) if values else 0


def _important_rows(rows) -> list[dict]:
    important_types = {"Hotel", "Activity", "Transfer", "Train", "Flight", "Cruise", "Ferry", "Transport", "Arrival", "Departure", "Day Overview"}
    return [row for row in rows or [] if get_row_type(row) in important_types or row.get("type") in important_types]


def _city_set(rows) -> set[str]:
    return {str(row.get("city", "")).strip() for row in rows or [] if str(row.get("city", "")).strip()}


def validate_itinerary_integrity(parsed_rows) -> list[ItineraryValidationIssue]:
    """Return blocking/warning validation issues for parsed rows."""
    rows = list(parsed_rows or [])
    issues: list[ItineraryValidationIssue] = []
    important_rows = _important_rows(rows)
    main_rows = [row for row in important_rows if not is_optional_row(row)]
    optional_rows = [row for row in important_rows if is_optional_row(row)]

    input_max_day = _max_day(important_rows)
    main_max_day = _max_day(main_rows)
    optional_max_day = _max_day(optional_rows)

    if input_max_day and main_max_day and input_max_day - main_max_day >= 2:
        later_optional = [row for row in optional_rows if get_day_number(row.get("day", "")) > main_max_day]
        if later_optional:
            issues.append(ItineraryValidationIssue(
                "error",
                "main_itinerary_truncated_by_optional_rows",
                (
                    f"Input reaches Day {input_max_day}, but the included itinerary only reaches Day {main_max_day}. "
                    "Later rows were classified as optional. Review optional/add-on classification before generating the PDF."
                ),
            ))

    if optional_rows and main_rows:
        optional_count = len(optional_rows)
        important_count = max(len(important_rows), 1)
        if optional_count / important_count >= 0.45 and optional_max_day > main_max_day:
            issues.append(ItineraryValidationIssue(
                "error",
                "too_many_late_optional_rows",
                (
                    f"{optional_count} of {len(important_rows)} important rows are optional and optional rows extend beyond the included itinerary. "
                    "This usually means optional status leaked from supplier text."
                ),
            ))

    missing_cities = _city_set(important_rows) - _city_set(main_rows) - _city_set(optional_rows)
    if missing_cities:
        issues.append(ItineraryValidationIssue(
            "warning",
            "unclassified_destination_rows",
            f"Some destination rows were not classified into included or optional itinerary buckets: {', '.join(sorted(missing_cities))}.",
        ))

    return issues


def blocking_validation_messages(parsed_rows) -> list[str]:
    return [issue.message for issue in validate_itinerary_integrity(parsed_rows) if issue.severity == "error"]
