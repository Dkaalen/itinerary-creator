import re

from time_utils import format_duration_display
from parser_modules.common import clean_space

def normalize_ampm(value):
    suffix = str(value or "").replace(".", "").upper()
    if suffix in {"AM", "PM"}:
        return suffix
    return ""


def parse_time_token(value):
    text = clean_space(value)
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)?", text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    suffix = normalize_ampm(match.group(3) or "")

    if hour > 24 or minute > 59:
        return None

    return {
        "hour": hour,
        "minute": minute,
        "suffix": suffix,
        "raw": text,
    }


def format_12_hour(hour, minute, suffix=""):
    suffix = normalize_ampm(suffix)

    if suffix:
        display_hour = hour
        if display_hour == 0:
            display_hour = 12
        if display_hour > 12:
            display_hour = display_hour - 12
        return f"{display_hour}:{minute:02d} {suffix}"

    # Treat suffix-free times as 24-hour values. This standardizes colleague
    # inputs like 20:00, 18:00, and 08:30 - 22:30 into client-facing AM/PM.
    if hour == 0:
        return f"12:{minute:02d} AM"
    if 1 <= hour < 12:
        return f"{hour}:{minute:02d} AM"
    if hour == 12:
        return f"12:{minute:02d} PM"
    return f"{hour - 12}:{minute:02d} PM"


def format_time_token(value, default_suffix=""):
    parsed = parse_time_token(value)
    if not parsed:
        return clean_space(value)

    suffix = parsed["suffix"] or normalize_ampm(default_suffix)
    return format_12_hour(parsed["hour"], parsed["minute"], suffix)


def infer_range_suffixes(start, end):
    start_suffix = start["suffix"]
    end_suffix = end["suffix"]

    if start_suffix and not end_suffix:
        if start_suffix == "AM" and end["hour"] <= start["hour"]:
            end_suffix = "PM"
        else:
            end_suffix = start_suffix

    if end_suffix and not start_suffix:
        if end_suffix == "PM" and start["hour"] > end["hour"]:
            start_suffix = "AM"
        else:
            start_suffix = end_suffix

    return start_suffix, end_suffix


def find_clock_range(value):
    text = clean_space(value).replace("–", "-").replace("—", "-")
    # Require either a colon or an AM/PM suffix, so ranges like "5-8 minutes"
    # are not interpreted as 5:00 AM - 8:00 AM.
    token = r"\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?)?"
    pattern = re.compile(rf"(?<!\d)({token})\s*-\s*({token})(?!\d)", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        raw = match.group(0)
        after = text[match.end():match.end() + 15].lower()
        if "minute" in after or "min" in after:
            continue
        if ":" not in raw and not re.search(r"[AaPp]\.?[Mm]\.?", raw):
            continue
        return raw
    return ""


def find_single_clock_time(value):
    text = clean_space(value)
    match = re.search(r"(?<!\d)(\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?))(?!\d)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(?<!\d)(\d{1,2}:\d{2})(?!\d)", text)
    if match:
        after = text[match.end():match.end() + 15].lower()
        if "minute" not in after and "min" not in after:
            return match.group(1)
    return ""


def normalize_time_text(value):
    """Standardize itinerary times to AM/PM display format.

    Examples:
    20:00 -> 8:00 PM
    08:30 - 22:30 -> 8:30 AM - 10:30 PM
    7 PM -> 7:00 PM
    8-10 AM -> 8:00 AM - 10:00 AM
    """

    text = clean_space(value)
    if not text:
        return ""

    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()

    time_token = r"\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?)?"
    range_pattern = re.compile(
        rf"(?<!\d)({time_token})\s*-\s*({time_token})(?!\d)",
        flags=re.IGNORECASE,
    )

    def replace_range(match):
        raw_range = match.group(0)
        after = text[match.end():match.end() + 15].lower()
        if "minute" in after or "min" in after:
            return raw_range
        if ":" not in raw_range and not re.search(r"[AaPp]\.?[Mm]\.?", raw_range):
            return raw_range

        start_raw = match.group(1)
        end_raw = match.group(2)
        start = parse_time_token(start_raw)
        end = parse_time_token(end_raw)

        if not start or not end:
            return raw_range

        start_suffix, end_suffix = infer_range_suffixes(start, end)
        return f"{format_time_token(start_raw, start_suffix)} - {format_time_token(end_raw, end_suffix)}"

    text = range_pattern.sub(replace_range, text)

    # Normalize slash-separated alternatives and single remaining time tokens.
    single_pattern = re.compile(
        r"(?<!\d)(\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?|))(?!\s*(?:hours?|hrs?|hr)\b)(?!\d)",
        flags=re.IGNORECASE,
    )

    def replace_single(match):
        token = match.group(1).strip()
        parsed = parse_time_token(token)
        if not parsed:
            return match.group(0)

        # Avoid turning plain duration-like numbers into times. Single tokens
        # without AM/PM or a colon are too ambiguous to standardize safely.
        if not parsed["suffix"] and ":" not in token:
            return match.group(0)

        return format_time_token(token)

    text = single_pattern.sub(replace_single, text)
    text = re.sub(r"\(\s*anytime\s*\)", ", flexible start", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*flexible start", ", flexible start", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+\)", ")", text)
    return text.strip(" ,")


def normalize_duration_text(value):
    duration = clean_space(value)
    if not duration:
        return ""

    minute_match = re.search(r"\b(\d+\s*(?:-|–)\s*\d+\s*minutes?)\b", duration, flags=re.IGNORECASE)
    if minute_match:
        return minute_match.group(1).replace("-", "–")

    # Defensive cleanup: sometimes a colleague-style cell has
    # "3 Hrs Overview ..." in the same pipe section. Keep only the actual
    # duration phrase and discard any following supplier description.
    match = re.search(
        r"\b((?:Cruise\s+Duration|Tour\s+Duration|Duration)?\s*:?\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour))\b",
        duration,
        flags=re.IGNORECASE,
    )
    if match:
        duration = match.group(1)

    duration = re.sub(r"\bCruise\s+Duration\b", "Cruise duration", duration, flags=re.IGNORECASE)
    duration = re.sub(r"\bTour\s+Duration\b", "Duration", duration, flags=re.IGNORECASE)
    duration = re.sub(r"\bDuration\s*:\s*", "Duration ", duration, flags=re.IGNORECASE)
    return format_duration_display(duration)


def split_time_and_duration(value):
    text = clean_space(value)
    if not text:
        return "", ""

    duration = ""
    patterns = [
        r"\b(Cruise\s+Duration\s+\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour))\b",
        r"\b(Duration\s*:?\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour))\b",
        r"\b(\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour))\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            duration = normalize_duration_text(match.group(1))
            text = (text[:match.start()] + text[match.end():]).strip(" -|:")
            break

    text = re.sub(r"\b0(\d):(\d{2})\s*pm\b", r"\1:\2 pm", text, flags=re.IGNORECASE)
    text = re.sub(r"\b0(\d):(\d{2})\s*am\b", r"\1:\2 am", text, flags=re.IGNORECASE)

    return normalize_time_text(text), duration
