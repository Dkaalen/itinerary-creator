"""Norway in a Nutshell transport detection and labels."""

from __future__ import annotations

import re

from text_polish import polish_title


def _is_norway_in_a_nutshell_text(text):
    lower = str(text or "").lower()
    if "norway in a nutshell" in lower:
        return True
    has_flam = any(marker in lower for marker in ["flåm", "flam", "flåmsbana", "flamsbana", "flåm train", "flam train", "flåm railway", "flam railway"])
    has_fjord = any(marker in lower for marker in ["nærøyfjord", "naeroyfjord", "fjord cruise", "gudvangen", "voss"])
    return has_flam and has_fjord


def _norway_nutshell_route_label(text, fallback_origin="", fallback_destination=""):
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
    route_match = re.search(r"\b(Bergen|Oslo|Fl[åa]m|Voss|Gudvangen|Myrdal)\s+to\s+(Bergen|Oslo|Fl[åa]m|Voss|Gudvangen|Myrdal)\b", str(text or ""), flags=re.IGNORECASE)
    if route_match:
        origin, destination = polish_title(route_match.group(1)), polish_title(route_match.group(2))
    else:
        origin, destination = fallback_origin, fallback_destination
    if origin and destination and origin.lower() != destination.lower():
        return f"Norway in a Nutshell from {origin} to {destination}"
    if destination:
        return f"Norway in a Nutshell to {destination}"
    return "Norway in a Nutshell"


def has_norway_in_a_nutshell(rows):
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()
    return "norway in a nutshell" in text
