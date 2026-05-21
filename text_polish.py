"""
text_polish.py

Client-facing text cleanup helpers for itinerary output.
These helpers silently fix recurring supplier/input text issues before the
content reaches the preview or PDF. They are intentionally conservative:
only common itinerary artifacts are corrected, and the raw input remains
unchanged.
"""

from __future__ import annotations

import re


def clean_space(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


CASE_REPLACEMENTS = [
    (r"\bHScandic\b", "Scandic"),
    (r"\bMArina\b", "Marina"),
    (r"\bGrand\s+MArina\b", "Grand Marina"),
    (r"\bFunicual\b", "Funicular"),
    (r"\bFunicualr\b", "Funicular"),
    (r"\bComfort\s+hotel\b", "Comfort Hotel"),
    (r"\bquality\s+grand\b", "Quality Grand"),
    (r"\bscandic\b", "Scandic"),
    (r"\bthon\s+hotel\b", "Thon Hotel"),
    (r"\bhotel\s+mayfair\b", "Hotel Mayfair"),
    (r"\bsanta's\s+hotel\b", "Santa's Hotel"),
    (r"\bstandard\s+doubel\s+room\b", "Standard Double Room"),
    (r"\bstandard\s+double\s+room\b", "Standard Double Room"),
    (r"\bstandard\s+room\b", "Standard Room"),
]


def _apply_case_replacements(text: str) -> str:
    for pattern, replacement in CASE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def dedupe_or_similar(text: str) -> str:
    text = re.sub(r"\bor\s+Similar\b", "or similar", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:\s+or\s+similar){2,}", " or similar", text, flags=re.IGNORECASE)
    text = re.sub(r"\bor\s+similar\s+or\s+similar\b", "or similar", text, flags=re.IGNORECASE)
    return clean_space(text)


def remove_duplicate_service_phrase(text: str) -> str:
    """Remove repeated transfer/transport fragments from messy supplier cells."""
    text = clean_space(text)
    if not text:
        return ""

    # Specific but common artifact:
    # "Shuttle transfer from A to B Shuttle Transfer A to B"
    pattern = re.compile(
        r"\b(Shuttle transfer from\s+(.+?)\s+to\s+(.+?))\s+Shuttle\s+Transfer\s+\2\s+to\s+\3\b",
        flags=re.IGNORECASE,
    )
    text = pattern.sub(lambda m: m.group(1), text)

    # Generic adjacent duplicate phrase cleanup for short repeated tails.
    words = text.split()
    for n in range(3, min(10, len(words) // 2) + 1):
        first_tail = " ".join(words[-2 * n:-n]).lower()
        second_tail = " ".join(words[-n:]).lower()
        if first_tail == second_tail:
            return " ".join(words[:-n])

    return clean_space(text)


def _polish_text_fragment(text: str) -> str:
    """Polish one text fragment without intentionally preserving line breaks."""
    text = _apply_case_replacements(text)
    text = dedupe_or_similar(text)
    text = remove_duplicate_service_phrase(text)

    # Clean broken supplier inclusion fragments and recurring typo/casing issues.
    text = re.sub(r"\bRound-trip ferry is\b", "Round-trip ferry", text, flags=re.IGNORECASE)
    text = re.sub(r"\bKnowledgeable\s*,?\s*multilingual guide\b", "Knowledgeable, multilingual guide", text, flags=re.IGNORECASE)
    text = re.sub(r"\bEnglish\s+speaking\b", "English-speaking", text, flags=re.IGNORECASE)
    text = re.sub(r"\bA/C\b", "air-conditioned", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPick/Drop\b", "Pick-up/drop-off", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPick\s*up\b", "Pick-up", text, flags=re.IGNORECASE)
    text = re.sub(r"\bDrop\s*off\b", "drop-off", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpick-up/drop-off\b", "Pick-up/drop-off", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTour Guiding\b", "Local guide service", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTour guiding\b", "Local guide service", text, flags=re.IGNORECASE)
    text = re.sub(r"\bProfessional Camera Pictures\b", "Professional camera photos", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTour Transportation\b", "Transport during the tour", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTour transportation\b", "Transport during the tour", text, flags=re.IGNORECASE)
    text = re.sub(r"\bGoods\s*&\s*services tax\b", "Taxes and service fees", text, flags=re.IGNORECASE)
    text = re.sub(r"\bDSLR photography\b", "DSLR photography", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+)\s*KM\b", lambda m: f"{m.group(1)} km", text, flags=re.IGNORECASE)
    text = re.sub(r"\bRovaniemi City\b", "Rovaniemi city", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCookies\s*&\s*hot drinks\b", "Cookies and hot drinks", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCookies\s*&\s*Hot drinks\b", "Cookies and hot drinks", text, flags=re.IGNORECASE)
    text = re.sub(r"\bHot\s+drinks?\s*&\s*snacks?\s+or\s+cookies\b", "Hot drinks and snacks or cookies", text, flags=re.IGNORECASE)
    text = re.sub(r"\bHot\s+drinks?\s+and\s+snacks?\s+or\s+cookies\b", "Hot drinks and snacks or cookies", text, flags=re.IGNORECASE)

    # Normalize punctuation spacing, but never insert spaces inside clock times
    # such as 10:30 AM or 3:00 PM.
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"(?<!\d)([,.;])(?!\d)(?=\S)", r"\1 ", text)
    text = re.sub(r"(?<!\d):(?!\d)(?=\S)", ": ", text)
    text = re.sub(r"\b(\d{1,2}):\s+(\d{2})\s*([AP]M)\b", r"\1:\2 \3", text, flags=re.IGNORECASE)
    return clean_space(text)


def polish_client_text(value: str) -> str:
    """General client-facing text polish.

    Multiline supplier blocks must keep their line breaks because the parser uses
    those line breaks to create separate inclusion bullets. Earlier versions
    collapsed multiline text too early, which made several inclusions spill into
    one long bullet and into pick-up/drop-off fields.
    """
    if value is None:
        return ""

    text = str(value).replace("\xa0", " ")

    if "\n" in text:
        return "\n".join(_polish_text_fragment(line) for line in text.splitlines())

    return _polish_text_fragment(text)

def polish_hotel_name(value: str) -> str:
    text = polish_client_text(value)
    text = re.sub(r"\s+or\s+similar$", "", text, flags=re.IGNORECASE).strip()

    # Remove street-address suffixes that suppliers sometimes append to hotel
    # names, for example "Santa's Hotel Santa Claus Korkalonkatu 29".
    address_suffix = (
        r"\s+[A-ZÀ-ÝÆØÅÄÖ][A-Za-zÀ-ÿÆØÅÄÖæøåäö'’.-]*"
        r"(?:katu|gata|gatan|veien|vegen|vej|road|street|avenue|ave|lane|ln|boulevard|blvd)"
        r"\s+\d+[A-Za-z]?\s*$"
    )
    text = re.sub(address_suffix, "", text, flags=re.IGNORECASE).strip()

    text = dedupe_or_similar(text)
    return text


def polish_title(value: str) -> str:
    text = polish_client_text(value)
    text = dedupe_or_similar(text)
    return text.strip(" -:|")


def polish_inclusion_item(value: str, context_title: str = "") -> str:
    item = polish_client_text(value).strip(" •-*\t")
    lower = item.lower().strip(" :?.,")

    if not item:
        return ""

    remove_exact = {
        "what's included",
        "what’s included",
        "includes",
        "included",
        "what is included",
    }
    if lower in remove_exact:
        return ""

    broken_replacements = {
        "round-trip ferry is": "Round-trip ferry",
        "round trip ferry is": "Round-trip ferry",
    }
    if lower in broken_replacements:
        return broken_replacements[lower]

    if lower.endswith(" is") and len(item.split()) <= 5:
        item = item[:-3].strip()

    item = dedupe_or_similar(item)
    return item


def expand_compound_inclusion_item(item: str) -> list[str]:
    """Split only the supplier artifacts that commonly arrive as one bullet.

    This is intentionally conservative: normal phrases with commas, such as
    "Professional, English-speaking guide", remain together.
    """

    item = polish_inclusion_item(item)
    if not item:
        return []

    split_patterns = [
        r",\s*(?=English-speaking\b)",
        r",\s*(?=Knowledgeable\b)",
        r",\s*(?=Comfortable coach\b)",
        r",\s*(?=Northern Lights instructions\b)",
        r",\s*(?=Warm overalls\b)",
        r",\s*(?=Snacks\b)",
        r",\s*(?=Free photographs\b)",
        r",\s*(?=2-course\b)",
    ]

    parts = [item]
    for pattern in split_patterns:
        new_parts = []
        for part in parts:
            new_parts.extend(re.split(pattern, part, flags=re.IGNORECASE))
        parts = new_parts

    return [polish_inclusion_item(part) for part in parts if polish_inclusion_item(part)]


def polish_inclusion_items(items, context_title: str = "") -> list[str]:
    cleaned: list[str] = []

    for raw in items or []:
        expanded_items = expand_compound_inclusion_item(raw)
        for item in expanded_items:
            if not item:
                continue

            lower = item.lower()
            if cleaned:
                previous = cleaned[-1]
                previous_lower = previous.lower().strip(" ,")
                if lower in {"multilingual guide", "english-speaking guide", "small-group experience", "small group experience"} and previous_lower in {"knowledgeable", "personalized", "professional"}:
                    cleaned[-1] = f"{previous}, {item}"
                    continue
                if lower.startswith(("english-speaking", "multilingual", "small-group", "small group")) and previous_lower in {"knowledgeable", "personalized", "professional"}:
                    cleaned[-1] = f"{previous}, {item}"
                    continue
                if lower.startswith(("drinks", "drink")) and previous_lower in {"snacks", "snack"}:
                    cleaned[-1] = f"{previous}, {item}"
                    continue

            if item not in cleaned:
                cleaned.append(item)

    return cleaned

# ── Time + duration display helpers ───────────────────────────────────────────
# These helpers are intentionally kept in text_polish.py so parser, normalizer,
# preview rendering and PDF export can all use the same rule: when an activity
# has one clear start time plus a reliable duration, display a start-end range
# in the client-facing day-by-day itinerary.

def _time_clean(value: str) -> str:
    return clean_space(str(value or "").replace("–", "-").replace("—", "-"))


def _normalize_clock_token(value: str) -> str:
    text = _time_clean(value)
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)", text)
    if not match:
        return ""
    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    suffix = match.group(3).replace(".", "").upper()
    if hour < 1 or hour > 12 or minute > 59:
        return ""
    return f"{hour}:{minute:02d} {suffix}"


def _clock_to_minutes(value: str):
    text = _normalize_clock_token(value)
    if not text:
        return None
    match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(AM|PM)", text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    suffix = match.group(3)
    if suffix == "PM" and hour != 12:
        hour += 12
    if suffix == "AM" and hour == 12:
        hour = 0
    return hour * 60 + minute


def _minutes_to_clock(total_minutes: int) -> str:
    total_minutes = total_minutes % (24 * 60)
    hour24 = total_minutes // 60
    minute = total_minutes % 60
    suffix = "AM" if hour24 < 12 else "PM"
    hour12 = hour24 % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def parse_duration_minutes(value: str):
    """Return duration in minutes for common supplier duration strings."""
    text = _time_clean(value).lower()
    if not text:
        return None
    text = re.sub(r"^(?:duration|tour duration|ferry duration|cruise duration)\s*:?\s*", "", text, flags=re.IGNORECASE)

    total = 0
    hour_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|hr|h)\b", text, flags=re.IGNORECASE)
    minute_match = re.search(r"\b(\d+)\s*(?:minutes?|mins?|min|m)\b", text, flags=re.IGNORECASE)
    if hour_match:
        total += int(round(float(hour_match.group(1)) * 60))
    if minute_match:
        total += int(minute_match.group(1))
    return total or None


def expand_time_with_duration(time_value: str, duration_value: str) -> str:
    """Display start-end time when a single start time and duration are known.

    Examples:
    10:00 AM + 5 hours -> 10:00 AM - 3:00 PM
    8:00 PM + 4 hours -> 8:00 PM - 12:00 AM

    Existing ranges and alternative times are preserved.
    """
    raw_time = _time_clean(time_value)
    if not raw_time:
        return ""

    # Do not alter an existing range or alternative options.
    if re.search(r"\d\s*-\s*\d", raw_time) or "/" in raw_time:
        return raw_time

    start_display = _normalize_clock_token(raw_time)
    if not start_display:
        return raw_time

    start_minutes = _clock_to_minutes(start_display)
    duration_minutes = parse_duration_minutes(duration_value)
    if start_minutes is None or duration_minutes is None:
        return start_display

    # Keep guardrails conservative: this is meant for normal experiences, not
    # multi-day or vague durations.
    if duration_minutes < 15 or duration_minutes > 18 * 60:
        return start_display

    return f"{start_display} - {_minutes_to_clock(start_minutes + duration_minutes)}"

# Shared time/duration helpers are re-exported here for backward compatibility.
from time_utils import (
    parse_duration_minutes,
    expand_time_with_duration,
    format_duration_display,
    format_duration_minutes,
)
