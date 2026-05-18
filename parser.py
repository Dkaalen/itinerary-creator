import hashlib
import re

APP_FIX_VERSION = "2026-05-18 v4 day-boundary-hard-fix"

DETAIL_LABELS = [
    "Time",
    "Meeting point",
    "End point",
    "Includes",
    "Notable Sights",
    "Schedule",
    "Luggage included",
]

DETAIL_MARKERS = [f" - {label}:" for label in DETAIL_LABELS]
DAY_PATTERN = re.compile(r"^day\s+\d+\b", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$")


def extract_detail(text, label):
    marker = f"{label}:"

    if marker not in text:
        return ""

    after_marker = text.split(marker, 1)[1]

    for next_marker in DETAIL_MARKERS:
        if next_marker in after_marker:
            after_marker = after_marker.split(next_marker, 1)[0]

    return after_marker.strip(" -")


def clean_title(text):
    title = text

    for marker in DETAIL_MARKERS:
        if marker in title:
            title = title.split(marker, 1)[0]

    return title.strip()


def split_comma_list(text, *, protect_compound_phrases=False):
    if not text:
        return []

    if isinstance(text, list):
        return [str(item).strip() for item in text if item and str(item).strip()]

    parts = [item.strip() for item in text.split(",") if item.strip()]

    if not protect_compound_phrases:
        return parts

    merged = []
    attach_to_previous_prefixes = (
        "english-speaking",
        "english speaker",
        "english - speaker",
        "norwegian-speaking",
        "norwegian speaker",
        "sami-speaking",
        "van or coach",
        "coach or van",
        "bus or coach",
        "carry on",
    )

    for part in parts:
        lower = part.lower()

        if merged and lower.startswith(attach_to_previous_prefixes):
            merged[-1] = f"{merged[-1]}, {part}"
        else:
            merged.append(part)

    return merged


def detect_effective_type(item_type, title, details):
    combined = f"{title} {details}".lower().strip()

    if "flight to" in combined or combined.startswith("flight "):
        return "Flight"

    if "train to" in combined or "train transfer" in combined or "express train" in combined:
        return "Train"

    if "cruise to" in combined or "overnight cruise" in combined:
        return "Cruise"

    if "ferry to" in combined:
        return "Ferry"

    return item_type


def find_description_cell(parts):
    # Use the last non-empty Excel cell, not parts[-1]. This avoids empty copied columns.
    for part in reversed(parts):
        value = part.strip()
        if value:
            return value
    return ""


def make_row_id(day, item_type, start_date, end_date, description):
    source = "|".join([
        day.strip().lower(),
        item_type.strip().lower(),
        start_date.strip().lower(),
        end_date.strip().lower(),
        description.strip().lower(),
    ])
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]


def parse_itinerary(raw_text):
    rows = []
    seen_row_ids = set()
    current_day = ""

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = raw_line.rstrip("\n").split("\t")
        if not any(part.strip() for part in parts):
            continue

        first_cell = parts[0].strip() if len(parts) >= 1 else ""

        if first_cell:
            if not DAY_PATTERN.match(first_cell):
                continue
            current_day = first_cell

        if not current_day:
            continue

        item_type = parts[1].strip() if len(parts) >= 2 else ""
        start_date = parts[2].strip() if len(parts) >= 3 and DATE_PATTERN.match(parts[2].strip()) else ""
        end_date = parts[3].strip() if len(parts) >= 4 and DATE_PATTERN.match(parts[3].strip()) else ""
        description = find_description_cell(parts)

        if not item_type or not description:
            continue

        row_id = make_row_id(current_day, item_type, start_date, end_date, description)
        if row_id in seen_row_ids:
            continue
        seen_row_ids.add(row_id)

        row = {
            "raw": line,
            "line_number": line_number,
            "row_id": row_id,
            "day": current_day,
            "type": item_type,
            "effective_type": "",
            "start_date": start_date,
            "end_date": end_date,
            "city": "",
            "title": "",
            "details": description,
            "time": "",
            "meeting_point": "",
            "end_point": "",
            "notable_sights": [],
            "includes": [],
            "luggage_included": "",
        }

        if ":" in description:
            city, rest = description.split(":", 1)
            row["city"] = city.strip()
            main_text = rest.strip()
        else:
            main_text = description

        row["title"] = clean_title(main_text)
        row["time"] = extract_detail(main_text, "Time")
        row["meeting_point"] = extract_detail(main_text, "Meeting point")
        row["end_point"] = extract_detail(main_text, "End point")
        row["notable_sights"] = split_comma_list(extract_detail(main_text, "Notable Sights"))
        row["includes"] = split_comma_list(
            extract_detail(main_text, "Includes"),
            protect_compound_phrases=True,
        )
        row["luggage_included"] = extract_detail(main_text, "Luggage included")
        row["effective_type"] = detect_effective_type(row["type"], row["title"], row["details"])
        rows.append(row)

    return rows
