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
        if row_type in {"transfer", "transport"}:
            if row_tokens & {"train", "rail", "railway", "express", "overnight"}:
                hinted.add("train")
            if row_tokens & {"coach", "bus", "road", "route", "drive", "panorama"}:
                hinted.add("road journey")
    tokens = tokenize(" ".join(text_parts))
    return infer_themes(tokens) | hinted


def build_day_context(day: str, rows: list[dict]) -> dict:
    city = ""
    parts = [day]
    for row in rows or []:
        if not city and str(row.get("city", "")).strip():
            city = str(row.get("city", "")).strip()
        parts.append(_row_text(row))

    non_transport_rows = [
        row for row in (rows or [])
        if _row_type(row) not in {"transfer", "transport"}
    ]
    primary_rows = non_transport_rows or list(rows or [])

    text = " ".join(parts)
    tokens = tokenize(text)
    themes = infer_themes(tokens) | _themes_for_rows(rows or [])
    primary_themes = _themes_for_rows(primary_rows)
    return {
        "day": day,
        "city": city,
        "city_variants": city_variants(city),
        "tokens": tokens,
        "themes": themes,
        "primary_themes": primary_themes,
        "season": infer_season_from_rows(rows),
        "text": normalize_keyword(text),
    }


