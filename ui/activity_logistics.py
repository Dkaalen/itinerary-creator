"""Pickup, drop-off and meeting-point helpers for activity blocks."""

from __future__ import annotations

import re

from ui.render_text_helpers import clean_space, normalize_list


def detect_hotel_pickup_dropoff_text(value):
    """Return a clean pickup/drop-off phrase when supplier text says hotel pickup is included."""

    text = clean_space(value)
    if not text:
        return ""

    lower = text.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", lower)
    normalized = f" {clean_space(normalized)} "

    has_hotel_context = any(
        marker in normalized
        for marker in [
            " hotel ",
            " hotels ",
            " accommodation ",
            " accommodations ",
            " your hotel ",
            " selected hotel ",
            " centrally located hotel ",
            " central hotel ",
        ]
    )
    has_pickup = any(marker in normalized for marker in [" pick up ", " pickup ", " picked up ", " collection "])
    has_dropoff = any(marker in normalized for marker in [" drop off ", " dropoff ", " dropped off ", " return transfer "])

    if has_hotel_context and has_pickup and has_dropoff:
        return "Hotel pick-up and drop-off"

    if has_hotel_context and has_pickup:
        return "Hotel pick-up"

    # Compact supplier phrasing sometimes omits the word hotel in the exact
    # pickup phrase but still clearly says pickup/drop-off is included.
    if ("pick up drop off" in normalized or "pickup dropoff" in normalized or "pickup drop off" in normalized) and has_hotel_context:
        return "Hotel pick-up and drop-off"

    return ""


def clean_pickup_dropoff_value(value):
    """Normalize a pickup/drop-off detail for display."""

    text = clean_space(value).strip(" :.-")
    if not text:
        return ""

    hotel_phrase = detect_hotel_pickup_dropoff_text(text)
    if hotel_phrase:
        return hotel_phrase

    text = re.sub(r"^(pick[- ]?up\s*/\s*drop[- ]?off\s*)", "", text, flags=re.IGNORECASE).strip(" :.-")
    text = re.sub(r"^(pick[- ]?up\s+and\s+drop[- ]?off\s*)", "", text, flags=re.IGNORECASE).strip(" :.-")
    text = re.sub(r"^(pickup\s+and\s+dropoff\s*)", "", text, flags=re.IGNORECASE).strip(" :.-")

    # Sometimes supplier inclusions arrive as one comma-separated bullet such as
    # "Pick-up/drop-off in central Tromsø, English-speaking guide". Only the
    # actual logistics portion belongs in the day-by-day pickup line.
    text = re.split(
        r",\s*(?=(?:english[- ]speaking|knowledgeable|professional|comfortable|northern lights|warm |snacks|drinks|free photographs|2-course|tour transportation|guide)\b)",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" :.-")

    return text or value


def get_activity_logistics(row):
    """Return a practical meeting/pick-up line for the day-by-day block."""

    meeting_point = str(row.get("meeting_point") or "").strip()
    if meeting_point:
        hotel_phrase = detect_hotel_pickup_dropoff_text(meeting_point)
        if hotel_phrase:
            return "Pick-up/drop-off", hotel_phrase
        return "Meeting point", meeting_point

    for item in normalize_list(row.get("includes", [])):
        item_text = str(item).strip()
        lower = item_text.lower()

        hotel_phrase = detect_hotel_pickup_dropoff_text(item_text)
        if hotel_phrase:
            return "Pick-up/drop-off", hotel_phrase

        if (
            "pick-up/drop-off" in lower
            or "pickup/drop-off" in lower
            or "pick up/drop-off" in lower
            or "pick-up and drop-off" in lower
            or "pick up and drop off" in lower
            or "pickup and dropoff" in lower
        ):
            value = clean_pickup_dropoff_value(item_text)
            return "Pick-up/drop-off", value or item_text

        if lower.startswith("departure from") or "drop-off" in lower or "drop off" in lower:
            return "Departure/drop-off", item_text

    detail_text = " ".join(
        str(row.get(key) or "")
        for key in ["title", "original_title", "details", "client_description"]
    )
    hotel_phrase = detect_hotel_pickup_dropoff_text(detail_text)
    if hotel_phrase:
        return "Pick-up/drop-off", hotel_phrase

    return "", ""
