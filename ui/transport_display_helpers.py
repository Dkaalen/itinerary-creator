"""Transport display helpers for UI rendering."""

from __future__ import annotations

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged
from itinerary_generation.transport import is_route_transfer
from ui.render_text_helpers import normalize_list


def is_self_arranged_transport(row):
    return (get_row_type(row) in TRANSPORT_TYPES or is_route_transfer(row)) and is_self_arranged(row)


def is_self_transfer(row):
    row_type = get_row_type(row)
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()

    return row_type == "Transfer" and "self transfer" in text


def is_tallinn_ferry_day_trip(row):
    """Return True for Helsinki-Tallinn ferry-style day trip activities.

    Supplier rows often call the crossing a cruise ticket even though the
    client-facing product is a ferry-style Tallinn day trip. Keep this broad
    enough for self-guided and guided formats, but still tied to Tallinn.
    """

    context_text = " ".join(
        str(row.get(key) or "")
        for key in ["city", "title", "original_title", "details", "client_description"]
    ).lower()
    context_text += " " + " ".join(normalize_list(row.get("includes", []))).lower()

    mentions_tallinn = "tallinn" in context_text or "tallin" in context_text
    if not mentions_tallinn:
        return False

    # A day-trip title from Helsinki to Tallinn is enough context for the
    # duration label to be "Ferry duration" even when the raw row says cruise.
    if "day trip to tallinn" in context_text or "excursion to tallinn" in context_text or "excursion to tallin" in context_text:
        return True

    mentions_helsinki = "helsinki" in context_text
    crossing_marker = any(
        marker in context_text
        for marker in [
            "star class",
            "cruise ticket",
            "ferry ticket",
            "port transfer",
            "port transfers",
            "departure from helsinki",
            "departure from tallinn",
            "helsinki port",
            "ferry crossing",
        ]
    )

    return mentions_tallinn and (mentions_helsinki or crossing_marker) and crossing_marker
