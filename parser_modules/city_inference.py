"""City inference helpers for parser rows."""

import re

from place_aliases import canonicalize_place_name, is_known_place
from parser_modules.common import clean_space, is_valid_city_value


def infer_city_from_text(text):
    """Infer obvious Nordic city mentions from otherwise city-less titles."""

    source = clean_space(text)
    if not source:
        return ""
    patterns = [
        r"\bin\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\s*[,|:-]|\s*$)",
        r"\b(?:from|to)\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\s*[,|:-]|\s*$)",
        r"^([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})\s+(?:Hop|Walking|City|Sightseeing|Private|Shuttle|Airport|Leisure)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if not match:
            continue
        candidate = clean_space(match.group(1)).strip(" .,-|:")
        candidate = re.split(
            r"\s+(?:Guide|Ticket|Tour|Walk|Bus|Boat|Cruise|Safari|Transfer)\b",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" .,-|:")
        if candidate and is_valid_city_value(candidate) and is_known_place(candidate):
            return canonicalize_place_name(candidate)
    return ""


# Backwards-compatible alias for tests or legacy imports.
_infer_city_from_text = infer_city_from_text
