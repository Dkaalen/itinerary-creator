import re

from parser_modules.common import *  # noqa: F401,F403
from parser_modules.details import extract_detail, extract_between_markers, split_comma_list
from parser_modules.time_parsing import (
    find_clock_range,
    find_single_clock_time,
    normalize_duration_text,
    normalize_time_text,
    split_time_and_duration,
)

def _looks_like_pickup_window(text):
    lower = str(text or "").lower()
    return "before departure" in lower or "pick-up window" in lower or "pickup window" in lower


def extract_duration_from_description(main_text):
    main_text = re.sub(r"(\d)\s*\.\s*(\d)", r"\1.\2", str(main_text or ""))
    standard_time = extract_detail(main_text, "Time")
    _, duration = split_time_and_duration(standard_time)
    if duration:
        return duration

    # Prefer explicit duration labels, especially when supplier text also
    # contains pick-up windows such as "75–45 minutes before departure".
    explicit_patterns = [
        r"\bDuration\s*:?\s*(\d+(?:\s*[.,]\s*\d+)?\s*(?:-|–|to)\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour|h))\b",
        r"\bDuration\s*:?\s*(\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour|h))\b",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, main_text, flags=re.IGNORECASE)
        if match:
            return normalize_duration_text(match.group(1))

    pipe_parts = [clean_space(part) for part in main_text.split("|")]
    for part in pipe_parts[1:5]:
        if _looks_like_pickup_window(part):
            continue
        match = re.search(
            r"\b((?:Cruise\s+Duration|Tour\s+Duration|Duration)?\s*:?\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:-|–|to)?\s*\d*(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour|h))\b",
            part,
            flags=re.IGNORECASE,
        )
        if match:
            return normalize_duration_text(match.group(1))

    match = re.search(
        r"\b((?:Cruise\s+Duration|Tour\s+Duration|Duration)?\s*:?\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:-|–|to)?\s*\d*(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour|h))\b",
        main_text,
        flags=re.IGNORECASE,
    )
    if match and not _looks_like_pickup_window(main_text[match.start(): match.end() + 40]):
        return normalize_duration_text(match.group(1))

    minute_match = re.search(r"\b(\d+\s*(?:-|–)\s*\d+\s*minutes?)\b", main_text, flags=re.IGNORECASE)
    if minute_match and not _looks_like_pickup_window(main_text[minute_match.start(): minute_match.end() + 40]):
        return normalize_duration_text(minute_match.group(1))

    return ""


def extract_time_from_description(main_text):
    standard_time = extract_detail(main_text, "Time")

    if standard_time:
        clock_range = find_clock_range(standard_time)
        if clock_range:
            return normalize_time_text(clock_range)
        single_time = find_single_clock_time(standard_time)
        if single_time:
            return normalize_time_text(single_time)
        time_text, _ = split_time_and_duration(standard_time)
        return time_text

    # Pipe format examples:
    # "Title | 20:00 | 5 Hrs | ..."
    # "Title | 8-10 AM (Anytime) | 7 Hrs | ..."
    # "Oslo to Bergen | Norway in a Nutshell 08:25 - 20:40 | ..."
    pipe_parts = [clean_space(part) for part in main_text.split("|")]

    for part in pipe_parts[1:4]:
        lower = part.lower()
        if "hr" in lower or "hour" in lower or "minute" in lower:
            continue
        clock_range = find_clock_range(part)
        if clock_range:
            return normalize_time_text(clock_range)
        if re.search(r"\b12\s+noon\b|\bnoon\b", part, flags=re.IGNORECASE):
            return "12:00 PM"
        single_time = find_single_clock_time(part)
        if single_time:
            return normalize_time_text(single_time)
        spaced_time = re.match(r"^\s*(\d{1,2})\s+(\d{2})\s*(?:([AaPp]\.?[Mm]\.?))?\s*$", part)
        if spaced_time:
            suffix = spaced_time.group(3) or ""
            return normalize_time_text(f"{spaced_time.group(1)}:{spaced_time.group(2)} {suffix}".strip())

    clock_range = find_clock_range(main_text)
    if clock_range:
        return normalize_time_text(clock_range.replace(".", ":"))

    return ""

def extract_meeting_point_from_description(main_text):
    standard_meeting = extract_detail(main_text, "Meeting point")

    if standard_meeting:
        return standard_meeting

    section = extract_between_markers(
        main_text,
        [
            r"pick[-\s]*up\s*/\s*meeting\s*point",
            r"pickup\s*/\s*meeting\s*point",
            r"meeting\s*point\s*:",
            r"pick[-\s]*up\s*:",
        ],
        [
            r"\boverview\b",
            r"\bwhat'?s included\b",
            r"\bwhat’s included\b",
            r"\bwhat to expect\b",
            r"\bimportant info\b",
            r"\n\s*\n",
        ],
    )

    if section:
        return clean_space(section)

    # Some long supplier descriptions use prose rather than a label, for example
    # "Meet our guide near the University of Oslo". Keep only the useful point.
    meet_match = re.search(
        r"meet\s+(?:our\s+)?(?:your\s+)?guide\s+(near|at)\s+([^.,\n]+)",
        main_text,
        flags=re.IGNORECASE,
    )
    if meet_match:
        prep = meet_match.group(1).lower()
        place = clean_space(meet_match.group(2))
        if prep == "near":
            return f"Near {place}"
        return place

    return ""


def extract_includes_from_description(main_text):
    lower_full = main_text.lower()

    if "norway in a nutshell" in lower_full:
        includes = [
            "Bergen Railway",
            "Flåm Railway",
            "Fjord cruise",
            "Scenic bus journey",
        ]
        if "luggage porter" in lower_full:
            includes.append("Luggage porter service")
        return includes

    standard_includes = extract_detail(main_text, "Includes")

    if standard_includes:
        return split_comma_list(standard_includes, protect_compound_phrases=True)

    section = extract_between_markers(
        main_text,
        [
            r"what'?s included\??",
            r"what’s included\??",
            r"\bincludes\s*:\s*",
            r"(?<!not\s)\bincluded\s*:\s*",
            r"\binclude\s*[,|:]\s*",
        ],
        [
            r"pick[-\s]*up\s*/\s*meeting\s*point",
            r"pickup\s*/\s*meeting\s*point",
            r"\bmeeting\s*point\b",
            r"\boverview\b",
            r"\bnot\s+in(?:cl|lc)uded\b",
            r"\bwhat to expect\b",
            r"\bimportant info\b",
            r"\bour floating suits\b",
        ],
    )

    if section:
        return split_comma_list(section, protect_compound_phrases=True)

    # Some colleague/supplier rows use pipe sections without a formal
    # "What's included?" label, for example:
    # Title | 10 AM | 4 Hrs | guide, pickup, lunch | Pick up / meeting point ...
    # Treat the post-duration pipe section as inclusions when it looks like a
    # short inclusion list, but stop before any formal meeting-point section.
    pipe_parts = [clean_space(part) for part in main_text.split("|")]
    if len(pipe_parts) >= 4:
        pipe_candidates = []
        for part in pipe_parts[3:]:
            lower_part = part.lower()
            if any(marker in lower_part for marker in ["overview", "what to expect", "not included"]):
                continue
            part = re.split(r"pick[-\s]*up\s*/\s*meeting\s*point|pickup\s*/\s*meeting\s*point|meeting\s*point\s*:", part, flags=re.IGNORECASE)[0].strip(" :|-")
            if not part:
                continue
            if len(part) > 450:
                continue
            lower_part = part.lower()
            inclusion_markers = [
                "included", "ticket", "pick-up", "pickup", "drop-off", "lunch",
                "certificate", "transport", "guide", "meal", "snack", "drink",
                "photograph", "camera", "tax", "overalls", "tripod", "ferry",
                "equipment", "berry juice", "hot berry", "winter", "admission",
                "entry", "access", "ritual", "mask", "towel", "bathrobe", "locker",
            ]
            prose_markers = [
                "tour gives", "take a stroll", "listen to", "make sense",
                "to top it all", "waterworld", "best way to understand",
            ]
            marker_hits = sum(1 for marker in inclusion_markers if marker in lower_part)
            looks_like_prose = any(marker in lower_part for marker in prose_markers)
            looks_like_list = marker_hits >= 1 and (part.count(",") >= 1 or marker_hits >= 2) and not looks_like_prose
            if looks_like_list:
                pipe_candidates.extend(split_comma_list(part, protect_compound_phrases=True))
        if pipe_candidates:
            return polish_inclusion_items(pipe_candidates)

    lower = main_text.lower()
    fallback_includes = []

    if "ticket" in lower and "included" in lower:
        fallback_includes.append("Tickets included")

    if "luggage porter" in lower:
        fallback_includes.append("Luggage porter service included")

    return fallback_includes


def extract_luggage_included(main_text):
    luggage = extract_detail(main_text, "Luggage included")

    if luggage:
        return luggage

    if "luggage" in main_text.lower() and "included" in main_text.lower():
        for part in re.split(r"[-|]", main_text):
            if "luggage" in part.lower() and "included" in part.lower():
                return clean_space(part)

    return ""
