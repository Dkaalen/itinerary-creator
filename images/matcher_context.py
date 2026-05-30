"""Day-context construction for image matching."""

from __future__ import annotations

from .metadata import city_variants, infer_season_from_rows, infer_themes, normalize_keyword, tokenize


def _row_type(row: dict) -> str:
    return normalize_keyword(row.get("effective_type") or row.get("type") or "")


def _row_text(row: dict) -> str:
    return " ".join([
        str(row.get("city", "") or ""),
        str(row.get("title", "") or ""),
        str(row.get("original_title", "") or ""),
        str(row.get("details", "") or ""),
        str(row.get("display_description", "") or ""),
        " ".join(row.get("includes", []) or []),
    ])


def _themes_for_rows(rows: list[dict]) -> set[str]:
    text_parts = []
    hinted = set()
    for row in rows or []:
        row_type = _row_type(row)
        row_text = _row_text(row)
        row_tokens = tokenize(row_text)
        text_parts.append(row_text)
        if row_type in {"hotel", "accommodation", "arrival", "departure"}:
            hinted.add("city")
        if row_type in {"transfer", "transport", "drive", "car"}:
            if row_tokens & {"train", "rail", "railway", "express", "overnight"}:
                hinted.add("train")
            if row_tokens & {"coach", "bus", "road", "route", "drive", "driving", "vehicle", "car"}:
                hinted.add("road journey")
    tokens = tokenize(" ".join(text_parts))
    return infer_themes(tokens) | hinted


def _select_primary_image_city(rows: list[dict]) -> str:
    """Pick the destination that should drive day-image matching.

    Do not blindly use the first city on the day. Self-drive itineraries often
    start a day with arrival/car/drive rows in the origin city while the page
    heading and main experience are in the destination city. Activity rows are
    the best first signal, followed by accommodation, then travel/departure rows.
    """

    priority_groups = [
        {"activity", "day overview"},
        {"hotel", "accommodation"},
        {"train", "flight", "cruise", "ferry", "transport", "transfer"},
        {"arrival", "departure", "leisure", "drive", "car"},
    ]
    for group in priority_groups:
        for row in rows or []:
            row_type = _row_type(row)
            city = str(row.get("city", "") or "").strip()
            if city and row_type in group:
                return city
    for row in rows or []:
        city = str(row.get("city", "") or "").strip()
        if city:
            return city
    return ""


def _all_city_variants(rows: list[dict], primary_city: str) -> set[str]:
    variants = set(city_variants(primary_city))
    for row in rows or []:
        row_type = _row_type(row)
        city = str(row.get("city", "") or "").strip()
        if not city:
            continue
        # Keep activity/hotel cities as secondary matches. Avoid adding every
        # origin city from drive/car rows because that can make generic origin
        # images beat the day's actual destination.
        if row_type in {"activity", "hotel", "accommodation", "day overview"}:
            variants.update(city_variants(city))
    return variants


def build_day_context(day: str, rows: list[dict]) -> dict:
    city = _select_primary_image_city(rows or [])
    parts = [day]
    for row in rows or []:
        parts.append(_row_text(row))

    non_transport_rows = [
        row for row in (rows or [])
        if _row_type(row) not in {"transfer", "transport", "drive", "car"}
    ]
    primary_rows = non_transport_rows or list(rows or [])

    text = " ".join(parts)
    tokens = tokenize(text)
    themes = infer_themes(tokens) | _themes_for_rows(rows or [])
    primary_themes = _themes_for_rows(primary_rows)
    return {
        "day": day,
        "city": city,
        "city_variants": _all_city_variants(rows or [], city),
        "tokens": tokens,
        "themes": themes,
        "primary_themes": primary_themes,
        "season": infer_season_from_rows(rows),
        "text": normalize_keyword(text),
    }
