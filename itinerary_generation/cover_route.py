"""Shared cover-route formatting for HTML, PDF and editor previews."""

from __future__ import annotations

from html import escape

from itinerary_generation.common import (
    get_display_destination_city,
    is_valid_destination_city,
    main_rows_only,
)

SEPARATOR = " · "


def route_cities_with_return(parsed_rows: list[dict]) -> list[str]:
    """Return display cities for the cover route, preserving real return loops."""

    route: list[str] = []
    for row in main_rows_only(parsed_rows):
        city = get_display_destination_city(str(row.get("city", "")).strip())
        if not city or not is_valid_destination_city(city):
            continue
        if not route or city != route[-1]:
            route.append(city)

    if len(route) >= 3 and route[-1] == route[0]:
        result: list[str] = []
        for city in route[:-1]:
            if city not in result:
                result.append(city)
        result.append(route[-1])
        return result

    result: list[str] = []
    for city in route:
        if city not in result:
            result.append(city)
    return result


def create_cover_route_line(parsed_rows: list[dict]) -> str:
    cities = route_cities_with_return(parsed_rows)
    if not cities:
        return "Destinations will be detected from the itinerary text"
    return SEPARATOR.join(cities)


def split_route_line(route_line: str) -> list[str]:
    return [part.strip() for part in str(route_line or "").split("·") if part.strip()]


def balanced_cover_route_lines(route_line: str) -> list[str]:
    """Return visual cover-route lines with no lonely final destination."""

    parts = split_route_line(route_line)
    if len(parts) < 5:
        return [SEPARATOR.join(parts)] if parts else ([str(route_line).strip()] if str(route_line or "").strip() else [])
    return [SEPARATOR.join(parts[:-2]), SEPARATOR.join(parts[-2:])]


def cover_route_html(route_line: str) -> str:
    """Return escaped HTML for the cover route using shared line balancing."""

    parts = split_route_line(route_line)
    if not parts:
        return escape(str(route_line or ""))
    if len(parts) < 2:
        return escape(parts[0])

    if len(parts) >= 5:
        head = SEPARATOR.join(escape(part) for part in parts[:-2])
        tail = f'<span class="cover-destination-pair">{escape(parts[-2])}&nbsp;·&nbsp;{escape(parts[-1])}</span>'
        return f"{head}<br>{tail}"

    tail = f'<span class="cover-destination-pair">{escape(parts[-2])}&nbsp;·&nbsp;{escape(parts[-1])}</span>'
    head = [escape(part) for part in parts[:-2]]
    return SEPARATOR.join(head + [tail])
