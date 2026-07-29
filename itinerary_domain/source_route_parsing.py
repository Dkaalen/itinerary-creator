"""Neutral source-text route parsing for downstream domain enrichment."""
from __future__ import annotations

import re
from collections.abc import Callable

from itinerary_domain.source_place_values import is_valid_city_value, normalize_place_name
from shared.source_text_cleanup import fix_common_text
from shared.text import clean_space

_INVALID_ROUTE_ORIGINS = {
    "",
    "drive",
    "flight",
    "train",
    "transfer",
    "shuttle transfer",
    "self transfer",
    "coach",
    "bus",
    "ferry",
    "cruise",
    "scenic train",
    "scenic train transfer",
    "long distance panorama coach transfer",
    "atlantic ocean cruise",
    "arrival",
}
_INVALID_ROUTE_DESTINATIONS = {"hotel", "station", "airport", "accommodation"}
_ROUTE_MODE_PREFIX_RE = re.compile(
    r"^(?:scenic\s+)?(?:flight|train|coach|bus|ferry|cruise)(?:\s+transfer)?\s*[:|]?\s*",
    flags=re.IGNORECASE,
)
_ROUTE_DETAIL_SPLIT_RE = re.compile(
    r"\s+-\s+(?:departure|arrival|time|includes|included|excludes|luggage|cabin)\b|"
    r"\s+\|\s+(?:departure|arrival|time|includes|included|excludes|final\s+timing|voucher)\b",
    flags=re.IGNORECASE,
)
_ROUTE_TRAILING_DETAIL_RE = re.compile(
    r"\s+part\s+\d+\b|\s+\d{1,2}:\d{2}|\s+-\s+(?:bus|coach|flight|train)\b|"
    r"\s+bus\s+\d+\b|\s+time\b|\s+departure\b|\s+arrival\b|\s*\|",
    flags=re.IGNORECASE,
)
_ONBOARD_DETAIL_RE = re.compile(r"\s+onboard\b|\s+on\s+board\b|\s+at\s+\d{1,2}:\d{2}", flags=re.IGNORECASE)


def _valid_route_pair(origin: str, destination: str) -> tuple[str, str]:
    if origin and destination and origin.lower() != destination.lower():
        return origin, destination
    return "", ""


def _repair_missed_to(source: str) -> str:
    return re.sub(
        r"\b(Flight|Train|Coach|Bus|Cruise|Ferry)\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,35}?)\s+o\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,35}?)(?=\s+(?:self[-\s]*arranged|cost|price)|\s*$)",
        r"\1 \2 to \3",
        source,
        flags=re.IGNORECASE,
    )


def _route_source_and_prefix(text: str) -> tuple[str, str]:
    source = _repair_missed_to(fix_common_text(text).replace("–", "-"))
    route_source = _ROUTE_DETAIL_SPLIT_RE.split(source, maxsplit=1)[0]

    prefix_origin = ""
    prefix_match = re.match(r"^([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+):\s*(.+)$", route_source)
    if prefix_match and is_valid_city_value(prefix_match.group(1)):
        prefix_origin = normalize_place_name(prefix_match.group(1))
        route_source = prefix_match.group(2)

    route_source = re.sub(r"\bself[-\s]*(?:arranged|arrange|arrnaged|arrnage)\b", "", route_source, flags=re.IGNORECASE)
    route_source = re.sub(r"\b(?:cost|price)\s+not\s+in(?:cl|lc)uded\b", "", route_source, flags=re.IGNORECASE)
    return route_source, prefix_origin


def _scheduled_route_points(route_source: str) -> tuple[str, str]:
    scheduled_places = []
    for schedule_match in re.finditer(
        r"\b\d{1,2}[:.]\s*\d{2}(?:\s*[ap]m)?\s+(?P<place>[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,45}?)(?=\s+(?:via|direct|arrival|with|\d{1,2}[:.]\s*\d{2})|\s*[|,;)]|\s*$)",
        route_source,
        flags=re.IGNORECASE,
    ):
        place = normalize_place_name(schedule_match.group("place"))
        if place and is_valid_city_value(place) and place.lower() not in {"am", "pm", "morning train"}:
            scheduled_places.append(place)

    has_timed_dash_route = re.search(
        r"\d{1,2}[:.]\s*\d{2}\s+[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,45}?\s*-\s*\d{1,2}[:.]\s*\d{2}",
        route_source,
        flags=re.IGNORECASE,
    )
    if len(scheduled_places) >= 2 and not has_timed_dash_route and re.search(
        r"\b(?:norway\s+in\s+a\s+nutshell|train|flight|bus|coach|ferry|cruise)\b",
        route_source,
        flags=re.IGNORECASE,
    ):
        return _valid_route_pair(scheduled_places[0], scheduled_places[-1])
    return "", ""


def _named_group_route_points(
    route_source: str,
    pattern: str,
    *,
    require_match: Callable[[str], bool] | None = None,
) -> tuple[str, str]:
    if require_match and not require_match(route_source):
        return "", ""
    match = re.search(pattern, route_source, flags=re.IGNORECASE)
    if not match:
        return "", ""
    origin = normalize_place_name(match.group("origin"))
    destination_raw = re.sub(r"^(?:from|to)\s+", "", match.group("destination"), flags=re.IGNORECASE)
    destination = normalize_place_name(destination_raw)
    return _valid_route_pair(origin, destination)


def _timed_leg_route_points(route_source: str) -> tuple[str, str]:
    timed_legs = list(
        re.finditer(
            r"\b(?:bus|coach|train|flight|ferry|cruise)\s+\d{1,2}[:.]\s*\d{2}\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s*-\s*\d{1,2}[:.]\s*\d{2}\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?=\s*(?:\+|\||\(|$))",
            route_source,
            flags=re.IGNORECASE,
        )
    )
    if not timed_legs:
        return "", ""
    origin = normalize_place_name(timed_legs[0].group("origin"))
    destination = normalize_place_name(timed_legs[-1].group("destination"))
    return _valid_route_pair(origin, destination)


def _clean_route_origin(raw: str, prefix_origin: str) -> str:
    origin = normalize_place_name(_ROUTE_MODE_PREFIX_RE.sub("", raw).strip(" -:|."))
    return prefix_origin if origin.lower() in _INVALID_ROUTE_ORIGINS else origin


def _clean_route_destination(raw: str) -> str:
    destination_raw = _ROUTE_TRAILING_DETAIL_RE.split(raw, maxsplit=1)[0].strip(" -:|.")
    destination_raw = _ONBOARD_DETAIL_RE.split(destination_raw, maxsplit=1)[0].strip(" -:|.")
    return normalize_place_name(destination_raw)


def _is_rejected_route_destination(destination: str) -> bool:
    return destination.lower() in _INVALID_ROUTE_DESTINATIONS or bool(
        re.search(r"shared in voucher|final timing|voucher", destination, flags=re.IGNORECASE)
    )




def _self_drive_route_points(route_source: str, prefix_origin: str) -> tuple[str, str]:
    match = re.search(
        r"^\s*(?:self[-\s]*)?drive\s+to\s+(?P<destination>.+?)(?:\s+-\s+|\s+\||,|$)",
        route_source,
        flags=re.IGNORECASE,
    )
    if not match or not prefix_origin:
        return "", ""
    destination = _clean_route_destination(match.group("destination"))
    if _is_rejected_route_destination(destination):
        return "", ""
    return _valid_route_pair(prefix_origin, destination)

def _explicit_transport_route_points(route_source: str, prefix_origin: str) -> tuple[str, str]:
    transport_route = re.search(
        r"\b(?:flight|train|coach|bus|ferry|cruise)(?:\s+transfer)?\s*(?:[:|])?\s*(.+?\s+to\s+.+)$",
        route_source,
        flags=re.IGNORECASE,
    )
    if not transport_route:
        return "", ""
    route_text = clean_space(transport_route.group(1)).strip(" -:|.")
    if prefix_origin and route_text.lower().startswith("to "):
        route_text = f"{prefix_origin} {route_text}"
    pieces = [clean_space(part).strip(" -:|.") for part in re.split(r"\s+to\s+", route_text, flags=re.IGNORECASE) if clean_space(part).strip(" -:|.")]
    if len(pieces) < 2:
        return "", ""
    origin = _clean_route_origin(pieces[0], prefix_origin)
    destination = _clean_route_destination(pieces[-1])
    if _is_rejected_route_destination(destination):
        return "", ""
    return origin, destination


def _generic_to_route_points(route_source: str, prefix_origin: str) -> tuple[str, str]:
    patterns = [
        r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+-\s+|\s+\|\s+|,|$)",
        r"\|\s*([^|\n]+?)\s+to\s+([^|\n]+?)\s*(?:\||$)",
        r"\b([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ\s]+?)(?:\s+-\s+|\s+\|\s+|,|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, route_source, flags=re.IGNORECASE)
        if not match:
            continue
        origin = _clean_route_origin(match.group(1), prefix_origin)
        destination = _clean_route_destination(match.group(2))
        if _is_rejected_route_destination(destination):
            continue
        return origin, destination
    return "", ""


def extract_route_points(text):
    """Returns (origin, destination) from common route phrasings.

    The helper is deliberately route-based, not itinerary-specific. It handles
    simple transport rows ("Train: Oslo to Bergen") and multi-leg rows where an
    intermediate stop appears before the final destination ("Copenhagen to
    Malmö to Stockholm").
    """

    route_source, prefix_origin = _route_source_and_prefix(text)
    route_attempts = (
        _scheduled_route_points(route_source),
        _named_group_route_points(
            route_source,
            r"^\s*(?:train|bus|coach|flight)\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäöÖ .'-]{2,35}?)\s+(?P<destination>[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?:\s*[|,;.]|\s+\d|$)",
            require_match=lambda value: not bool(re.search(r"\s+to\s+", value, flags=re.IGNORECASE)),
        ),
        _named_group_route_points(
            route_source,
            r"^\s*(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s+to\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?):\s*Norway\s+in\s+a\s+Nutshell\b",
        ),
        _timed_leg_route_points(route_source),
        _named_group_route_points(
            route_source,
            r"(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s*-\s*(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s+Night\s+train\b",
            require_match=lambda value: bool(re.search(r"\btrain\b", value, flags=re.IGNORECASE)),
        ),
        _named_group_route_points(
            route_source,
            r"\bfrom\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?:\s+bus\s+st(?:a|sa)ion|\s+station)?\b.+?\breaching\s+(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?:\s+at\b|\s+resort\b|\s*[,|.]|$)",
        ),
        _named_group_route_points(
            route_source,
            r"\b(?:day\s+|overnight\s+)?(?:train|flight|coach|bus|cruise|ferry)\b[^\n|,;:]{0,20}[,:]?\s+(?P<origin>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s*-\s*(?P<destination>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)(?:\n|\s+(?:intercity|ic|train|flight|coach|bus|cruise|ferry|self[-\s]*arranged|cost|price)\b|\s+\d{1,2}:\d{2}|$)",
        ),
        _self_drive_route_points(route_source, prefix_origin),
        _explicit_transport_route_points(route_source, prefix_origin),
        _generic_to_route_points(route_source, prefix_origin),
    )
    return next((route for route in route_attempts if route != ("", "")), ("", ""))



__all__ = ["extract_route_points"]
