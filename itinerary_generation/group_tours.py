"""Helpers for supplier-style multi-day group tour rows.

Group-tour overviews are different from ordinary activities: one long overview
cell can contain the package name, included accommodation placeholders, and
supplier day numbers. These helpers keep that information structured so the day
pages and inclusion summary can stay client-facing instead of dumping raw
supplier prose into the PDF.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Iterable

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title


def _clean(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def _day_number(value: str) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def is_group_tour_overview(row: dict) -> bool:
    text = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    return bool(
        row.get("effective_type") == "Day Overview"
        or row.get("type") == "Day Overview"
    ) and any(marker in text for marker in ["group tour", "holiday package", "what's included", "what’s included"])


def _trim_supplier_title_candidate(value: str) -> str:
    title = _clean(value).strip(" .:-|")
    # If parser cleanup has flattened the first prose sentence into the title,
    # cut at common sentence starters that follow supplier day headings.
    title = re.split(
        r"\s+(?=We\s|You\s|The\s|A\s+\d|Prepare\s|Once\s|After\s|At\s|On\s)",
        title,
        maxsplit=1,
    )[0].strip(" .:-|")
    title = re.sub(r"\bJökulsárlón\s*&\s*Ice Caves\b", "Jökulsárlón Glacier Lagoon & Ice Caves", title, flags=re.IGNORECASE)
    return title


def extract_supplier_day_title(text: str) -> str:
    """Return a clean title from strings like 'Day 3: Discover the Golden Circle'."""
    source = str(text or "").strip()
    for line in source.splitlines() or [source]:
        match = re.search(r"^\s*Day\s*\d+\s*:\s*([^|]+)", line, flags=re.IGNORECASE)
        if match:
            title = _trim_supplier_title_candidate(match.group(1))
            if title:
                title = re.sub(r"\s+&\s+", " & ", title)
                return polish_title(title)
    match = re.search(r"(?:^|\n|\|)\s*Day\s*\d+\s*:\s*([^\n|]+)", source, flags=re.IGNORECASE)
    if not match:
        return ""
    title = _trim_supplier_title_candidate(match.group(1))
    title = re.sub(r"\s+&\s+", " & ", title)
    return polish_title(title)


def supplier_day_number(row: dict) -> int:
    text = f'{row.get("original_title", "")}\n{row.get("details", "")}\n{row.get("title", "")}'
    match = re.search(r"(?:^|\n|\|)\s*Day\s*(\d+)\s*:", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _normalise_accommodation_phrase(raw: str) -> tuple[str, str, str]:
    """Return (hotel_name, city, meal_plan) for a group-tour accommodation line."""
    text = _clean(raw).strip(" .:-")
    text = re.sub(r"\bw\s*/\s*breakfast\b", "with breakfast", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbreakfast\b", "breakfast", text, flags=re.IGNORECASE)
    meal = "breakfast" if "breakfast" in text.lower() else ""
    text = re.sub(r"\bwith breakfast\b", "", text, flags=re.IGNORECASE).strip(" ,.-")

    lower = text.lower()
    accommodation_type = "accommodation"
    if "guesthouse" in lower:
        accommodation_type = "guesthouse accommodation"
    elif "hotel" in lower:
        accommodation_type = "hotel accommodation"

    place_text = re.sub(r"\b(?:hotel|guesthouse|accommodation)\b", "", text, flags=re.IGNORECASE).strip(" ,.-")
    place_text = polish_client_text(place_text)
    city = canonicalize_place_name(place_text) if place_text else ""

    if place_text and place_text.lower().startswith("countryside"):
        return "Countryside guesthouse accommodation", "", meal

    if city:
        return accommodation_type[:1].upper() + accommodation_type[1:], city, meal

    return accommodation_type[:1].upper() + accommodation_type[1:], "", meal


def extract_group_tour_accommodation_stays(rows: Iterable[dict]) -> list[dict]:
    """Extract accommodation placeholders from group-tour overview rows.

    Returned entries use supplier day numbers. A line such as
    'Day 2–3: West Iceland guesthouse w/breakfast' becomes a stay that should be
    placed on supplier day 2 / the corresponding itinerary day.
    """
    stays: list[dict] = []
    seen: set[tuple[int, str, str]] = set()

    for row in rows or []:
        if not is_group_tour_overview(row):
            continue
        text = str(row.get("details") or row.get("original_title") or row.get("title") or "")
        text = text.replace("–", "-").replace("—", "-")
        for raw_line in text.splitlines():
            line = _clean(raw_line).strip(" •-*|:")
            if not line:
                continue
            match = re.match(r"Day\s*(\d+)\s*(?:-\s*(\d+))?\s*:\s*(.+)$", line, flags=re.IGNORECASE)
            if not match:
                continue
            description = _clean(match.group(3))
            if not re.search(r"\b(hotel|guesthouse|accommodation)\b", description, flags=re.IGNORECASE):
                continue
            start_day = int(match.group(1))
            end_day = int(match.group(2) or match.group(1))
            hotel_name, city, meal = _normalise_accommodation_phrase(description)
            key = (start_day, hotel_name.lower(), city.lower())
            if key in seen:
                continue
            seen.add(key)
            stays.append(
                {
                    "supplier_day": start_day,
                    "supplier_end_day": end_day,
                    "hotel_name": hotel_name,
                    "city": city,
                    "meal_plan": meal,
                    "source_text": description,
                }
            )
    return stays


def add_group_tour_accommodation_rows(rows: list[dict]) -> list[dict]:
    """Add synthetic hotel rows for package accommodation placeholders.

    These rows only appear when the supplier overview gives placeholder stays
    rather than named hotels. They let the day pages and inclusion page tell the
    client where they sleep without inventing property names.
    """
    updated = [deepcopy(row) for row in rows or []]
    stays = extract_group_tour_accommodation_stays(updated)
    if not stays:
        return updated

    overview_days = [_day_number(row.get("day", "")) for row in updated if is_group_tour_overview(row)]
    base_day = min([day for day in overview_days if day] or [1])
    existing_keys = {
        (_day_number(row.get("day", "")), _clean(row.get("hotel_name") or row.get("title")).lower(), _clean(row.get("city")).lower())
        for row in updated
        if (row.get("effective_type") or row.get("type")) == "Hotel"
    }

    synthetic_rows: list[dict] = []
    for stay in stays:
        itinerary_day_number = base_day + int(stay["supplier_day"]) - 1
        day_label = f"Day {itinerary_day_number}"
        hotel_name = stay["hotel_name"]
        city = stay["city"]
        key = (itinerary_day_number, hotel_name.lower(), city.lower())
        if key in existing_keys:
            continue
        row = {
            "raw": stay.get("source_text", ""),
            "line_number": 0,
            "row_id": f"group-accommodation-{itinerary_day_number}-{len(synthetic_rows) + 1}",
            "is_optional": False,
            "is_group_tour_accommodation": True,
            "day": day_label,
            "type": "Hotel",
            "effective_type": "Hotel",
            "start_date": "",
            "end_date": "",
            "city": city,
            "title": hotel_name,
            "original_title": hotel_name,
            "details": stay.get("source_text", ""),
            "time": "",
            "duration": "",
            "meeting_point": "",
            "end_point": "",
            "notable_sights": [],
            "includes": [],
            "luggage_included": "",
            "hotel_name": hotel_name,
            "hotel_nights": "1",
            "room_category": "",
            "meal_plan": stay.get("meal_plan", ""),
        }
        synthetic_rows.append(row)
        existing_keys.add(key)

    if not synthetic_rows:
        return updated

    combined = updated + synthetic_rows
    combined.sort(key=lambda row: (_day_number(row.get("day", "")), 1 if row.get("is_group_tour_accommodation") else 0, int(row.get("line_number") or 0)))
    return combined


_OPTIONAL_EXTRA_LINE_RE = re.compile(r"\boptional\b\s+(.+)$", flags=re.IGNORECASE)
_OPTIONAL_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÝÞÆÖáðéíóúýþæöøåäöØÅÄÖ]+", flags=re.IGNORECASE)


def _tokens_for_optional_match(value: str) -> set[str]:
    tokens = {re.sub(r"s$", "", token.lower()) for token in _OPTIONAL_TOKEN_RE.findall(str(value or ""))}
    stop = {"optional", "tour", "entrance", "admission", "activity", "experience", "person", "per", "fee", "the", "and", "or", "at", "to", "from"}
    return {token for token in tokens if token not in stop and len(token) > 2}


def extract_optional_group_tour_extra_titles(rows: Iterable[dict]) -> list[str]:
    """Return optional extra names from group-tour overview NOT INCLUDED sections."""

    extras: list[str] = []
    for row in rows or []:
        if not is_group_tour_overview(row):
            continue
        source = str(row.get("details") or row.get("original_title") or row.get("title") or "")
        in_not_included = False
        for raw in source.replace("–", "-").splitlines():
            line = _clean(raw).strip(" •-*|:")
            if not line:
                continue
            lower = line.lower()
            if re.match(r"^not\s+included\b", lower):
                in_not_included = True
                continue
            if in_not_included and re.match(r"^(what\s+to\s+expect|what'?s\s+included|what’s\s+included|overview|itinerary)\b", lower):
                in_not_included = False
                continue
            if not in_not_included:
                continue
            match = _OPTIONAL_EXTRA_LINE_RE.search(line)
            if not match:
                continue
            title = match.group(1)
            title = re.sub(r"\([^)]*(?:€|\$|£|NOK|SEK|DKK|ISK|USD|EUR|GBP|kr|/person)[^)]*\)", "", title, flags=re.IGNORECASE)
            title = re.sub(r"\b\d[\d.,]*\s*(?:€|\$|£|NOK|SEK|DKK|ISK|USD|EUR|GBP|kr)\b", "", title, flags=re.IGNORECASE)
            title = re.sub(r"\b(?:tour|entrance|admission|activity|experience)\b\s*$", lambda m: m.group(0), title, flags=re.IGNORECASE)
            title = polish_title(_clean(title).strip(" .:-"))
            if title and title not in extras:
                extras.append(title)
    return extras


def annotate_group_tour_optional_extras(rows: list[dict]) -> list[dict]:
    """Mark main activity rows that are named as optional extras in the group overview.

    This does not delete the row.  It prevents inclusion builders from stating
    that the optional paid extra is included when the package overview says it is
    excluded.
    """

    updated = [deepcopy(row) for row in rows or []]
    optional_titles = extract_optional_group_tour_extra_titles(updated)
    optional_token_sets = [_tokens_for_optional_match(title) for title in optional_titles]
    optional_token_sets = [tokens for tokens in optional_token_sets if tokens]
    if not optional_token_sets:
        return updated
    for row in updated:
        if (row.get("effective_type") or row.get("type")) != "Activity":
            continue
        title_tokens = _tokens_for_optional_match(f'{row.get("title", "")} {row.get("original_title", "")}')
        clean_title_tokens = _tokens_for_optional_match(row.get("title", ""))
        for tokens in optional_token_sets:
            # Only flag the activity when the title itself is essentially the
            # optional extra.  Do not flag broad days such as "Discover Glaciers,
            # Ice Caves & Diamond Beach" just because one optional cave is named
            # in the prose.
            whale_optional = "whale" in tokens and "whale" in clean_title_tokens
            if tokens and (
                tokens <= clean_title_tokens
                or whale_optional
                or (len(tokens & clean_title_tokens) >= max(1, min(len(tokens), 2)) and len(clean_title_tokens) <= len(tokens) + 2)
            ):
                row["group_tour_optional_extra"] = True
                row["suppress_fallback_inclusions"] = True
                break
    return updated
