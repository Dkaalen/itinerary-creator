"""
normalizer.py

Post-parser normalization layer for itinerary rows.

The parser should focus on extracting structure from messy pasted input. This
module then applies conservative client-facing cleanup to the structured rows
before the generator, preview, and PDF layers use them.

No layout logic lives here. No facts are invented here.
"""

from __future__ import annotations

import copy
import re
from collections import Counter

import diagnostics
from generator import create_client_activity_title, clean_include_item, get_row_type
from place_aliases import canonicalize_place_name, is_known_place, is_likely_service_text
from text_polish import (
    polish_client_text,
    polish_hotel_name,
    polish_inclusion_items,
    polish_title,
)


def _clean_space(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def _day_number(row_or_day: object) -> int:
    if isinstance(row_or_day, dict):
        value = row_or_day.get("day", "")
    else:
        value = row_or_day
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else 0


def normalize_title_for_row(row: dict) -> str:
    """Return the preferred client-facing title for a structured row."""

    row_type = get_row_type(row)

    if row_type == "Activity":
        title = create_client_activity_title(row) or row.get("title", "")
        return polish_title(title)

    if row_type == "Hotel":
        return polish_hotel_name(row.get("hotel_name") or row.get("title") or "")

    return polish_title(row.get("title", ""))


def normalize_inclusion_list(items, context_title: str = "") -> list[str]:
    """Normalize inclusion bullets without changing what is included."""

    cleaned = []
    for item in items or []:
        item = clean_include_item(item, context_title)
        item = polish_client_text(item)
        if item:
            cleaned.append(item)

    return polish_inclusion_items(cleaned, context_title)


def normalize_itinerary_rows(parsed_rows: list[dict]) -> list[dict]:
    """Return normalized copies of parsed rows.

    This is the main bridge between itinerary_parser.py and generator/app.py.
    """

    normalized_rows = copy.deepcopy(parsed_rows or [])

    for row in normalized_rows:
        row_type = get_row_type(row)
        row["original_title"] = row.get("original_title") or row.get("title", "")

        if row.get("city"):
            row["city"] = canonicalize_place_name(polish_client_text(row.get("city", "")))
            warn_if_suspicious_city(row)

        if row.get("title"):
            row["title"] = normalize_title_for_row(row)

        if row_type == "Hotel":
            if row.get("hotel_name"):
                row["hotel_name"] = polish_hotel_name(row.get("hotel_name", ""))
                row["title"] = row["hotel_name"]
            if row.get("room_category"):
                row["room_category"] = polish_client_text(row.get("room_category", ""))
            if row.get("meal_plan"):
                row["meal_plan"] = polish_client_text(row.get("meal_plan", ""))

        for key in ["details", "duration", "meeting_point", "end_point", "luggage_included", "client_description"]:
            if row.get(key):
                row[key] = polish_client_text(row.get(key, ""))

        if isinstance(row.get("notable_sights"), list):
            row["notable_sights"] = polish_inclusion_items(row.get("notable_sights", []), row.get("title", ""))

        if isinstance(row.get("includes"), list):
            row["includes"] = normalize_inclusion_list(row.get("includes", []), row.get("title", ""))

    return normalized_rows


def warn_if_suspicious_city(row: dict) -> None:
    """Add an internal warning when city extraction looks questionable."""

    city = _clean_space(row.get("city", ""))
    if not city:
        return

    # Known aliases/canonicals are fine. Service text should already be filtered
    # elsewhere, but warn rather than block if something suspicious slipped in.
    if is_known_place(city):
        return

    if len(city) > 18 and not is_likely_service_text(city):
        diagnostics.warn(
            "unrecognised_city",
            f"City '{city}' on {row.get('day', 'Unknown day')} is not in the known place list — verify it is correct",
            raw_value=row.get("raw", city),
        )


LEISURE_VARIANTS = [
    "The rest of the day is left open, giving you space to settle in, explore nearby streets, enjoy a relaxed meal, or take the destination at your own pace.",
    "This free time keeps the day comfortably paced, with room to rest, wander locally, or shape the remaining hours around your own interests.",
    "Time at leisure is included so the schedule stays relaxed, leaving space for a quiet meal, a short walk, or independent exploration.",
    "The day also includes unstructured time, allowing you to slow down, enjoy the surroundings, or add your own discoveries along the way.",
    "A flexible pause is built into the day, giving you breathing room between arrangements and time to enjoy the destination independently.",
]


def create_leisure_text(row: dict | None = None) -> str:
    """Return deterministic varied free-time wording."""

    index = (_day_number(row or {}) - 1) % len(LEISURE_VARIANTS)
    return LEISURE_VARIANTS[index]


def contextualize_activity_section_titles(activity_sections: list[dict]) -> list[dict]:
    """Add city context to repeated activity inclusion headings where helpful.

    This keeps repeated generic headings such as "Northern Lights Chase" easier
    to understand on the activity inclusions pages.
    """

    sections = [dict(section) for section in activity_sections or []]
    title_counts = Counter(_clean_space(section.get("title", "")) for section in sections)

    seen_contextual_titles = set()
    for section in sections:
        title = _clean_space(section.get("title", ""))
        city = _clean_space(section.get("city", ""))

        if not title or title_counts[title] <= 1 or not city:
            continue

        should_contextualize = (
            "northern lights" in title.lower()
            or "aurora" in title.lower()
            or title_counts[title] > 1
        )

        if not should_contextualize:
            continue

        contextual_title = f"{title} in {city}"
        if contextual_title not in seen_contextual_titles:
            section["title"] = contextual_title
            seen_contextual_titles.add(contextual_title)

    return sections


def has_suspicious_client_text(value: str) -> bool:
    text = str(value or "").lower()
    markers = [
        "åre provided",
        "english - speaker",
        "mini bus",
        "little snack",
        "best aurora spots",
    ]
    return any(marker in text for marker in markers)


def warn_about_suspicious_output_rows(rows: list[dict]) -> None:
    """Internal QC warning for raw fragments that should not reach output."""

    for row in rows or []:
        text = " ".join(
            str(row.get(key) or "")
            for key in ["title", "details", "meeting_point", "client_description"]
        )
        text += " " + " ".join(str(item) for item in row.get("includes", []) or [])
        if has_suspicious_client_text(text):
            diagnostics.warn(
                "client_text_polish",
                f"Suspicious supplier wording remains on {row.get('day', 'Unknown day')}",
                raw_value=row.get("raw", text)[:500],
            )
