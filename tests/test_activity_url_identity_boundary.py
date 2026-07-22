from __future__ import annotations

from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.to_itinerary_input import calculator_state_to_raw_input
from itinerary_domain.activity_products import fingerprint_activity
from itinerary_generation.client_sanitizer import sanitize_client_text
from itinerary_generation.description_composer import compose_activity_description
from itinerary_generation.titles import create_client_activity_title
from itinerary_parser import parse_itinerary
from parser_modules.rows import make_row_id


OSLOFJORD_TITLE = "Oslo: Electric Oslofjord Sightseeing Cruise"
OSLOFJORD_DESCRIPTION = (
    "Description: Cruise silently through the Oslofjord, passing Akershus Fortress, "
    "the Opera House, MUNCH, picturesque islands and Dyna Lighthouse, with the option "
    "to disembark at the Bygdøy museum peninsula."
)
OSLOFJORD_URL = "https://booknordics.com/norway/eastern-norway/oslo/oslofjord-sightseeing-cruise"


def _raw_input(*, url: str = OSLOFJORD_URL) -> str:
    details = (
        f"{OSLOFJORD_TITLE} - Time: 11:00 AM - 1:00 PM - "
        "Meeting point: Rådhusbrygge 4, Platform E - "
        "Includes: Two-hour Oslofjord cruise aboard a 100% electric boat, "
        "app-based audio guide and optional stop at the Bygdøy museum peninsula - "
        f"{OSLOFJORD_DESCRIPTION} - URL: {url}"
    )
    return f"Day 2\tActivity\t\t23.07.2026\t\t\t\t\t{details}"


def test_calculator_keeps_url_out_of_generator_text() -> None:
    state = CalculatorState(
        rows=(
            CalculatorRow(
                row_id="stable-row",
                day="Day 2",
                type="Activity",
                from_date="23.07.2026",
                travel_element=OSLOFJORD_TITLE,
                comments=OSLOFJORD_DESCRIPTION,
                url=OSLOFJORD_URL,
            ),
        )
    )

    raw = calculator_state_to_raw_input(state)

    assert OSLOFJORD_TITLE in raw
    assert OSLOFJORD_DESCRIPTION in raw
    assert "URL:" not in raw
    assert OSLOFJORD_URL not in raw


def test_parser_extracts_url_metadata_without_changing_historical_row_id() -> None:
    raw = _raw_input()
    description = raw.split("\t")[-1]
    expected_id = make_row_id("Day 2", "Activity", "23.07.2026", "", description)

    row = parse_itinerary(raw)[0]

    assert row["row_id"] == expected_id
    assert row["source_url"] == OSLOFJORD_URL
    assert row["source_urls"] == [OSLOFJORD_URL]
    assert OSLOFJORD_URL not in row["raw"]
    assert "URL:" not in row["details"]


def test_oslofjord_identity_cannot_be_replaced_by_incidental_munch_reference() -> None:
    row = parse_itinerary(_raw_input())[0]

    title = create_client_activity_title(row)
    fingerprint = fingerprint_activity(row)
    description = compose_activity_description(row).text

    assert title == "Electric Oslofjord Sightseeing Cruise"
    assert fingerprint is not None
    assert fingerprint.canonical_family == "oslofjord_cruise"
    assert "Munch Museum Visit" not in title
    assert "booknordics.com" not in description
    assert "URL:" not in description


def test_misleading_url_slug_cannot_change_activity_identity() -> None:
    row = parse_itinerary(_raw_input(url="https://example.com/munch-museum-entrance-tickets"))[0]

    assert create_client_activity_title(row) == "Electric Oslofjord Sightseeing Cruise"
    assert fingerprint_activity(row).canonical_family == "oslofjord_cruise"


def test_genuine_munch_museum_ticket_remains_supported() -> None:
    raw = (
        "Day 2\tActivity\t\t23.07.2026\t\t\t\t\t"
        "Oslo: MUNCH Museum Entrance Tickets - Time: Flexible - Includes: Admission ticket"
    )
    row = parse_itinerary(raw)[0]

    assert create_client_activity_title(row) == "Munch Museum Visit"
    assert fingerprint_activity(row).canonical_family == "munch_museum_ticket"


def test_saved_damaged_url_tail_is_removed_by_final_client_boundary() -> None:
    damaged = (
        "Ride the Fløibanen funicular and enjoy the view. "
        "URL: https: //www. Mount Fløyen."
    )

    cleaned = sanitize_client_text(damaged)

    assert cleaned == "Ride the Fløibanen funicular and enjoy the view."
    assert "URL" not in cleaned
    assert "https" not in cleaned
