"""Boundary rules for splitting compact titles from supplier prose.

This module owns the title/prose boundary heuristics used by the parser.  It is
kept separate from ``title_cleanup`` so that the public title-cleanup function
can stay an orchestrator instead of becoming a catch-all for every corpus rule.
"""

from __future__ import annotations

import re

from shared.text import clean_space


_PRODUCT_NAME_PATTERN = re.compile(
    r"\b([A-ZÀ-Ý][A-Za-zÀ-ÿøØåÅäÄöÖ' -]{4,70}?\b(?:Tour|Safari|Cruise|Excursion|Experience|Ticket))\b"
)
_PRODUCT_ON_PATTERN = re.compile(
    r"\bon\s+the\s+([A-ZÀ-Ý][^.!?]{8,90}?\b(?:Tour|Experience|Safari|Cruise|Excursion|Package|Holiday))\b"
)
_PRODUCT_TITLE_END_RE = re.compile(
    r"\b(?:Waterfall|Waterfalls|Tour|Experience|Safari|Cruise|Excursion|Ticket|Tickets|Card|Package|Beach|Cave|Caves|Lagoon|Village|Museum|Cathedral|Church|Hotel|Igloo|Igloos)\b",
    flags=re.IGNORECASE,
)
_GENERIC_SUPPLIER_START_RE = re.compile(
    r"^(?:after|start|begin|today|make|take|enjoy|embark|discover|experience|join|prepare)\b",
    flags=re.IGNORECASE,
)

# These patterns identify where a compact heading turns into body prose.  The
# splitter chooses the earliest safe match, not the first rule listed, because
# real supplier cells often contain many later prose markers as well.
_PROSE_BOUNDARY_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\s+Make your way\b",
        r"\s+The day starts\b",
        r"\s+The journey continues\b",
        r"\s+The scenery continues\b",
        r"\s+This day is filled\b",
        r"\s+This tour will start\b",
        r"\s+We will start\b",
        r"\s+We continue\b",
        r"\s+On this,? our final day\b",
        r"\s+Your journey begins\b",
        r"\s+Your next destination\b",
        r"\s+Prepare to explore\b",
        r"\s+You will visit\b",
        r"\s+You will be\b",
        r"\s+You will travel\b",
        r"\s+You will head\b",
        r"\s+You(?:'|’)ll\b",
        r"\s+An unforgettable\b",
        r"\s+The first stop\b",
        r"\s+Embark on\b",
        r"\s+Experience the\b",
        r"\s+After Pick[- ]?up\b",
        r"\s+After (?:(?:a|the|a delightful|a delicious) |we(?:'|’)ve had (?:a|the|our) |enjoying (?:a |the )?)?(?:delicious )?breakfast\b",
        r"\s+Start your day\b",
        r"\s+Start the day\b",
        r"\s+Today'?s journey\b",
        r"\s+Today,? you\b",
        r"\s+On this day\b",
        r"\s+On (?:the|your) final day\b",
        r"\s+Continuing your journey\b",
        r"\s+Your adventure begins\b",
        r"\s+A\s+\d{2,4}m\b",
        r"\s+Seljalandsfoss\s*:\b",
        r"\s+Bring a raincoat\b",
        r"\s+Our adventure\b",
        r"\s+the adventure begins\b",
        r"\s+where you can\b",
        r"\s+visiting\b",
        r"\s+incl\.?\s+pick[-\s]*up\b",
        r"\s+Tickets?\s+ONly\b",
        r"\s+Purchase your card\b",
        r"\s+Drive Iceland\b",
        r"\s+Visit Þingvellir\b",
        r"\s+[A-ZÀ-Ý][A-Za-zÀ-ÿøØåÅäÄöÖ'-]+\s+is\s+(?:an?|the)\s+",
    ]
)



def extract_supplier_prose_product_name(source: str) -> str:
    """Extract a compact product name from a sentence-style supplier title."""

    source = clean_space(source)
    if not _GENERIC_SUPPLIER_START_RE.match(source):
        return ""

    match = _PRODUCT_ON_PATTERN.search(source) or _PRODUCT_NAME_PATTERN.search(source)
    if match:
        candidate = clean_space(match.group(1)).strip(" -:|,.")
        if 8 <= len(candidate) <= 85 and not re.search(r"\b(?:begins|followed|where|while|before|after)\b", candidate, flags=re.IGNORECASE):
            return candidate

    visit_match = re.search(
        r"\bvisit\s+to\s+([A-ZÀ-Ý][A-Za-zÀ-ÿøØåÅäÄöÖ' -]{3,60}?)(?:,|\s+known\b|\s+where\b|\s+before\b|\.)",
        source,
    )
    if visit_match:
        candidate = clean_space(visit_match.group(1)).strip(" -:|,.")
        if 4 <= len(candidate) <= 70:
            if re.search(r"\b(?:tour|cruise|safari|excursion|experience|ticket|visit)\b", candidate, flags=re.IGNORECASE):
                return candidate
            return f"{candidate} Visit"

    return ""



def _earliest_safe_boundary(source: str) -> int | None:
    matches = [match.start() for pattern in _PROSE_BOUNDARY_PATTERNS if (match := pattern.search(source)) and match.start() >= 8]
    return min(matches) if matches else None



def _compact_special_supplier_title(source: str) -> str:
    """Return compact titles for recurring non-prose supplier title shapes."""

    if re.match(r"^(?:pick[- ]?up|pick up).{0,40}rental (?:vehicle|car)\b", source, flags=re.IGNORECASE):
        return "Pick-up rental car"
    if re.match(r"^[A-ZÀ-Ý][^•]{0,45}\b(?:Electric|SUV|similar)\b.*\bpick[- ]?up\b.*\brental (?:vehicle|car)\b", source, flags=re.IGNORECASE):
        return "Pick-up rental car"
    if re.match(r"^self drive day\b", source, flags=re.IGNORECASE):
        return "Self-drive exploration day"
    if re.match(r"^explore\s+\*", source, flags=re.IGNORECASE):
        return "Self-drive exploration day"
    if re.match(r"^explore\s+(?:the\s+)?snæfellsnes\b", source, flags=re.IGNORECASE):
        return "Explore Snæfellsnes"
    if re.match(r"^icebreaker cruise will not be available\b", source, flags=re.IGNORECASE):
        return "Icebreaker cruise availability note"
    if re.match(r"^this day\s+\d+\b", source, flags=re.IGNORECASE):
        return "Guided tour upgrade note"

    ordinal_day = re.match(
        r"^On the (?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth) day, begin in ([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)(?:,|\s+then\b).*?\bTröllaskagi Peninsula\b",
        source,
        flags=re.IGNORECASE,
    )
    if ordinal_day:
        origin = clean_space(ordinal_day.group(1)).strip(" -:|,.")
        return f"{origin} and Tröllaskagi Peninsula" if origin else "Tröllaskagi Peninsula"

    star_hotel = re.match(r"^\d\s*Star,?\s+(.{4,70}?\bHotel)\b", source, flags=re.IGNORECASE)
    if star_hotel:
        return clean_space(star_hotel.group(1)).strip(" -:|,.")

    repeated_place = re.match(r"^(Free time to explore\s+(.{4,70}?))\s+\2(?:\s+-|\s+•|$)", source, flags=re.IGNORECASE)
    if repeated_place:
        return clean_space(repeated_place.group(1)).strip(" -:|,.")
    return ""


def _split_repeated_subject_title(source: str) -> str:
    """Split repeated lead-subject descriptions.

    Examples:
    ``Seljalandsfoss Waterfall Seljalandsfoss, ...`` -> ``Seljalandsfoss Waterfall``
    ``Jökulsárlón with Icecave Tour Jökulsárlón, ...`` -> ``Jökulsárlón with Icecave Tour``
    """

    words = re.findall(r"[A-Za-zÀ-ÿøØåÅäÄöÖ'&]+", source)
    if len(words) < 3:
        return source
    lead_word = words[0].lower().strip("'&")
    if len(lead_word) < 4:
        return source

    for match in _PRODUCT_TITLE_END_RE.finditer(source):
        if not 8 <= match.end() <= 95:
            continue
        candidate = clean_space(source[:match.end()]).strip(" -:|,.")
        rest = source[match.end():].lstrip(" -:|,.")
        if not candidate or candidate.lower().split()[0].strip("'&") != lead_word:
            continue
        if re.match(rf"{re.escape(words[0])}\b", rest, flags=re.IGNORECASE):
            return candidate
    return source



def _split_parenthetical_note(source: str) -> str:
    """Remove long list-style parenthetical notes from an otherwise compact title."""

    match = re.match(r"^(.{8,85}?)\s*\([^)]{25,}\)\s*$", source)
    if match:
        return match.group(1).strip(" -:|,.")

    if "(" in source:
        left, right = source.split("(", 1)
        left = clean_space(left).strip(" -:|,.")
        if 8 <= len(left) <= 85 and _PRODUCT_TITLE_END_RE.search(left) and re.search(r",|no entrance|no guide|museum|cathedral|university", right, flags=re.IGNORECASE):
            return left
    return source



def split_long_title_from_prose(title: str) -> str:
    """Keep headings compact when supplier body text follows the title."""

    source = clean_space(title)
    special_title = _compact_special_supplier_title(source)
    if special_title:
        return special_title

    product_name = extract_supplier_prose_product_name(source)
    if product_name:
        return product_name

    source = re.split(
        r"\s*,?\s*\d{1,2}[:.]\s*\d{2}\s+(?:duration|time)\b",
        source,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:|,.")

    repeated_title = _split_repeated_subject_title(source)
    if repeated_title != source:
        return repeated_title

    if len(source) <= 95 and not re.search(r"[.!?]", source):
        return _split_parenthetical_note(source)

    if ":" in source:
        left, right = source.split(":", 1)
        left = clean_space(left)
        right = clean_space(right)
        if (
            5 <= len(left) <= 70
            and not re.search(r"\d\s*$", left)
            and (
                re.search(r"\b(?:ticket|tickets|included|incl\.?|round trip|admission)\b", right, flags=re.IGNORECASE)
                or re.search(r"[.!?]", right)
                or len(right.split()) >= 10
            )
        ):
            return left

    boundary = _earliest_safe_boundary(source)
    if boundary is not None:
        return source[:boundary].strip(" -:|,.")

    source = re.split(
        r"\s+-\s+(?:[A-Za-zÀ-ÿøØåÅäÄöÖ\s]+\s+)?(?:port\s+)?transfers?\s+included\b|\s+-\s+self[-\s]*guided\b|\s+-\s+guided\s+tour\b|\s+○\s+",
        source,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:|,.")

    source = re.split(
        r"\s+with\s+private\s+transfer\b|\s+with\s+hotel\s+pick[-\s]*up\b",
        source,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:|,.")

    source = re.split(
        r"\s+-\s+(?:a\s+)?4x4\b|\s+-\s+(?:vehicle|car)\s+will\b",
        source,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:|,.")

    source = re.split(
        r",\s+(?:check\s+in|\d+x?night|shared|includes?|with|including|incl\.?|and\s+with|free\s+time|transfer(?:s)?|return\s+transfer|return\s+same\s+night)\b",
        source,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    source = re.split(r"\s+Includes\s+Breakfast\b", source, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|,.")
    source = _split_parenthetical_note(source)

    protected_source = re.sub(r"\bincl\.", "incl§", source, flags=re.IGNORECASE)
    sentence = re.split(r"(?<=[.!?])\s+", protected_source, maxsplit=1)[0].replace("incl§", "incl.")
    if len(sentence) >= 8 and len(sentence) < len(source):
        return sentence.strip(" -:|,.")

    return source.strip(" -:|,.")
