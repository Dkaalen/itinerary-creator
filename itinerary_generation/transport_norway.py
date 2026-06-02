"""Norway in a Nutshell transport detection and labels."""

from __future__ import annotations

import re

from text_polish import polish_title
from place_aliases import canonicalize_place_name


def _is_norway_in_a_nutshell_text(text):
    lower = str(text or "").lower()
    if "norway in a nutshell" in lower:
        return True
    has_flam = any(marker in lower for marker in ["flåm", "flam", "flåmsbana", "flamsbana", "flåm train", "flam train", "flåm railway", "flam railway"])
    has_fjord = any(marker in lower for marker in ["nærøyfjord", "naeroyfjord", "fjord cruise", "gudvangen", "voss"])
    return has_flam and has_fjord


def _clean_nutshell_place(value: str) -> str:
    return canonicalize_place_name(polish_title(str(value or "").strip(" -:|.,")))


def _direct_nutshell_pipe_route(text: str) -> tuple[str, str]:
    """Return the main route from compact pipe-style Nutshell rows.

    Supplier rows often arrive as ``Norway in a Nutshell | Oslo to Bergen |
    08:35 --- 20:38 | ...``.  That direct origin/destination should be kept
    as the product route.  Do not use this for long ``Route: Oslo to Myrdal,
    Myrdal to Flåm...`` descriptions, where the first internal leg would be
    misleading as the whole product route.
    """

    value = str(text or "")
    pipe_route = re.search(
        r"\|\s*([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*\|",
        value,
        flags=re.IGNORECASE,
    )
    if pipe_route:
        origin = _clean_nutshell_place(pipe_route.group(1))
        destination = _clean_nutshell_place(pipe_route.group(2))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

    prefix_route = re.search(
        r"^\s*([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)\s*\|\s*Norway\s+in\s+a\s+Nutshell",
        value,
        flags=re.IGNORECASE,
    )
    if prefix_route:
        origin = _clean_nutshell_place(prefix_route.group(1))
        destination = _clean_nutshell_place(prefix_route.group(2))
        if origin and destination and origin.lower() != destination.lower():
            return origin, destination

    return "", ""


def _norway_nutshell_route_label(text, fallback_origin="", fallback_destination=""):
    direct_origin, direct_destination = _direct_nutshell_pipe_route(str(text or ""))
    if direct_origin and direct_destination:
        return f"Norway in a Nutshell from {direct_origin} to {direct_destination}"

    explicit_destination_match = re.search(
        r"\bnorway\s+in\s+a\s+nutshell\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ ]+?)(?:\s+norway\s+in\s+a\s+nutshell|\s+-\s+|\s+\|\s+|$)",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    if explicit_destination_match:
        destination = polish_title(explicit_destination_match.group(1).strip())
        if fallback_origin and fallback_origin.lower() != destination.lower():
            return f"Norway in a Nutshell from {polish_title(fallback_origin)} to {destination}"
        return f"Norway in a Nutshell to {destination}"

    origin, destination = fallback_origin, fallback_destination
    if origin and destination and origin.lower() != destination.lower():
        return f"Norway in a Nutshell from {origin} to {destination}"
    if destination:
        return f"Norway in a Nutshell to {destination}"
    return "Norway in a Nutshell"


def has_norway_in_a_nutshell(rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()
    return "norway in a nutshell" in text
