"""Shared cover-route formatting for HTML, PDF and editor previews."""

from __future__ import annotations

from html import escape

from itinerary_generation.common import (
    destination_cities_for_row,
    main_rows_only,
    overnight_destination_cities,
)
from itinerary_generation.group_tour_rendering import group_tour_package_from_rows, group_tour_package_route

SEPARATOR = " · "


def _has_group_tour_overview(parsed_rows: list[dict]) -> bool:
    text = " ".join(
        f'{row.get("type", "")} {row.get("effective_type", "")} {row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'
        for row in parsed_rows or []
    ).lower()
    return any(marker in text for marker in ("group tour", "holiday package", "guided holiday"))


def _route_from_all_valid_day_cities(parsed_rows: list[dict]) -> list[str]:
    route: list[str] = []
    for row in main_rows_only(parsed_rows):
        for city in destination_cities_for_row(row):
            if not route or city != route[-1]:
                route.append(city)
    return route


def route_cities_with_return(parsed_rows: list[dict]) -> list[str]:
    """Return display cities for the cover route, preserving real return loops.

    The primary route is owned by confirmed overnight stays. Route-only
    transport rows are used only as a fallback when an itinerary has no
    accommodation rows at all.
    """

    route: list[str] = overnight_destination_cities(parsed_rows)
    package = group_tour_package_from_rows(parsed_rows)
    if package is not None:
        package_route = group_tour_package_route(package)
        start = route[0] if route else ""
        end = route[-1] if route else ""
        combined: list[str] = []
        for city in [start, *package_route, end]:
            if city and (not combined or city != combined[-1]):
                combined.append(city)
        if combined:
            route = combined
    # Packaged group tours often include several overnight regions inside one
    # overview row, while only the pre/post tour hotels are explicit Hotel rows.
    # In that case the client route should follow the day-by-day programme
    # cities instead of collapsing to Reykjavík only.
    if package is None and _has_group_tour_overview(parsed_rows) and len(route) <= 1:
        route = _route_from_all_valid_day_cities(parsed_rows)
    if not route:
        route = _route_from_all_valid_day_cities(parsed_rows)

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


def sanitize_route_line_for_overnights(parsed_rows: list[dict], route_line: str) -> str:
    """Filter an existing/saved route line to overnight destinations when known."""

    overnight = overnight_destination_cities(parsed_rows)
    if _has_group_tour_overview(parsed_rows) and len(overnight) <= 1:
        generated = route_cities_with_return(parsed_rows)
        return SEPARATOR.join(generated) if generated else str(route_line or "").strip()
    if not overnight:
        return str(route_line or "").strip()
    # The client-facing route is not an editable free-text summary.  It is owned
    # by confirmed overnight stays so old saved drafts cannot keep logistics
    # labels such as "your hotel", airports, rail stations or day-trip places.
    return SEPARATOR.join(overnight)


def clean_or_create_cover_route_line(parsed_rows: list[dict], route_line: str | None = None) -> str:
    if route_line:
        return sanitize_route_line_for_overnights(parsed_rows, route_line)
    return create_cover_route_line(parsed_rows)


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
