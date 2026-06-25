"""City inference helpers for parser rows."""

import re

from place_aliases import canonicalize_place_name, is_known_place
from parser_modules.common import clean_space, is_valid_city_value




def _leading_known_place(source: str) -> str:
    """Return a known place from the leading one to three title tokens."""

    match = re.match(r"^([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ.'-]+(?:\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ.'-]+){0,2})\b", source)
    if not match:
        return ""
    words = match.group(1).split()
    for width in range(min(3, len(words)), 0, -1):
        candidate = clean_space(" ".join(words[:width])).strip(" .,-|:")
        if candidate and is_valid_city_value(candidate) and is_known_place(candidate):
            return canonicalize_place_name(candidate)
    return ""

def infer_city_from_text(text):
    """Infer obvious Nordic city mentions from otherwise city-less titles."""

    source = clean_space(text)
    if not source:
        return ""
    leading_place = _leading_known_place(source)
    if leading_place and re.search(
        r"^(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ.'-]+\s*){1,3}(?:Hop|Walking|Roundtrip|Guided|City|Sightseeing|Private|Shuttle|Airport|Leisure|Northern|Fjord)\b",
        source,
    ):
        return leading_place

    patterns = [
        r"\b(?:meeting\s+point|pick[- ]?up\s*/\s*meeting\s+point|address|office)[^|\n]{0,140},\s*([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\s*[,|:-]|\s*$)",
        r"\bin\s+central\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\s*[,|:-]|\s|$)",
        r"\bin\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\s*[,|:-]|\s*$)",
        r"\b(?:from|to)\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\s*[,|:-]|\s*$)",
        r"^([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35}?)\s+(?:Hop|Walking|City|Sightseeing|Private|Shuttle|Airport|Leisure|Roundtrip|Guided)\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, source, flags=re.IGNORECASE):
            candidate = clean_space(match.group(1)).strip(" .,-|:")
            candidate = re.split(
                r"\s+(?:Guide|Ticket|Tour|Walk|Bus|Boat|Cruise|Safari|Transfer|City\s+Highlights)\b",
                candidate,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip(" .,-|:")
            if candidate and is_valid_city_value(candidate) and is_known_place(candidate):
                return canonicalize_place_name(candidate)
    return ""


# Backwards-compatible alias for tests or legacy imports.
_infer_city_from_text = infer_city_from_text
