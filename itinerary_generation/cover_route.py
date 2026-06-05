"""Shared cover-route formatting for HTML, PDF and editor previews."""

from __future__ import annotations

from html import escape

from itinerary_generation.common import (
    destination_cities_for_row,
    main_rows_only,
)

SEPARATOR = " · "


def route_cities_with_return(parsed_rows: list[dict]) -> list[str]:
    """Return display cities for the cover route, preserving real return loops."""

    route: list[str] = []
    for row in main_rows_only(parsed_rows):
        for city in destination_cities_for_row(row):
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
    """Return escaped HTML for the cover route using shared line balancing.

    The Streamlit visual preview and the PDF engine do not always wrap inline
    text the same way. Render explicit route lines as block spans so the final
    destination is not left alone in the browser preview while the PDF looks
    correct.
    """

    parts = split_route_line(route_line)
    if not parts:
        return escape(str(route_line or ""))
    if len(parts) < 2:
        return escape(parts[0])

    lines = balanced_cover_route_lines(SEPARATOR.join(parts))
    html_lines = []
    for line in lines:
        line_parts = split_route_line(line)
        if len(line_parts) >= 2:
            escaped = SEPARATOR.join(escape(part) for part in line_parts[:-2])
            pair = f'<span class="cover-destination-pair">{escape(line_parts[-2])}&nbsp;·&nbsp;{escape(line_parts[-1])}</span>'
            body = SEPARATOR.join([part for part in [escaped, pair] if part])
        else:
            body = escape(line_parts[0]) if line_parts else ""
        html_lines.append(f'<span class="cover-route-line">{body}</span>')
    return "<br>".join(html_lines)
