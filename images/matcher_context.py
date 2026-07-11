"""Coordinate day-context construction for image matching."""

from images.matcher_destination_context import (
    all_city_variants,
    country_variants_for_city,
    destination_profiles_for_city,
    known_destination_from_text,
)
from images.matcher_service_context import (
    row_text,
    row_type,
    service_destination_variants,
    service_intents_for_rows,
    themes_for_rows,
)
from images.metadata import (
    infer_primary_month_from_rows,
    infer_season_from_rows,
    infer_themes,
    normalize_keyword,
    tokenize,
)


def _select_primary_image_city(rows: list[dict]) -> str:
    priority_groups = (
        {"activity", "day overview"},
        {"hotel", "accommodation"},
        {"train", "flight", "cruise", "ferry", "transport", "transfer"},
        {"arrival", "departure", "leisure", "drive", "car"},
    )
    for group in priority_groups:
        for row in rows or []:
            city = str(row.get("city", "") or "").strip()
            kind = row_type(row)
            if not city or kind not in group:
                continue
            if kind in {"activity", "day overview"}:
                destination = known_destination_from_text(row_text(row), city)
                if destination:
                    return destination
            return city
    return next(
        (
            str(row.get("city", "") or "").strip()
            for row in rows or []
            if str(row.get("city", "") or "").strip()
        ),
        "",
    )


def build_day_context(day: str, rows: list[dict]) -> dict:
    rows = rows or []
    city = _select_primary_image_city(rows)
    text = " ".join([day, *[row_text(row) for row in rows]])
    tokens = tokenize(text)
    non_transport = [row for row in rows if row_type(row) not in {"transfer", "transport", "drive", "car"}]
    primary = non_transport or rows

    themes = infer_themes(tokens) | themes_for_rows(rows)
    primary_themes = themes_for_rows(primary)
    intents = service_intents_for_rows(rows)
    if intents & {"rail", "fjord_cruise", "coastal_cruise", "scenic_rail_fjord", "kayaking", "funicular"}:
        themes.update(intent.replace("_", " ") for intent in intents)

    city_values = all_city_variants(rows, city, row_type)
    city_values.update(service_destination_variants(intents, text))
    countries = country_variants_for_city(city)
    images, seasons = destination_profiles_for_city(city)

    for row in rows:
        row_city = str(row.get("city", "") or "").strip()
        countries.update(country_variants_for_city(row_city))
        row_images, row_seasons = destination_profiles_for_city(row_city)
        images.update(row_images)
        seasons.update(row_seasons)

    return {
        "day": day,
        "city": city,
        "city_variants": city_values,
        "country_variants": countries,
        "tokens": tokens,
        "themes": themes,
        "primary_themes": primary_themes,
        "season": infer_season_from_rows(rows),
        "month": infer_primary_month_from_rows(rows),
        "image_profiles": images,
        "season_profiles": seasons,
        "service_intents": intents,
        "text": normalize_keyword(text),
    }


__all__ = ["build_day_context"]
