import re

from parser_modules.common import *  # noqa: F401,F403
from parser_modules.time_parsing import normalize_duration_text, normalize_time_text

def standardize_row_text(row):
    """Applies client-facing cleanup after row parsing and effective type detection."""

    # Do not run the broad client-text polish on parsed time values.
    # Time fields are normalized by the dedicated time parser; broad punctuation
    # polish can corrupt clock syntax if it ever changes colon spacing.
    for key in ["city", "title", "details", "meeting_point", "end_point", "luggage_included", "hotel_name", "room_category", "meal_plan"]:
        if key in row and row.get(key):
            row[key] = fix_common_text(row[key])

    if row.get("time"):
        row["time"] = normalize_time_text(row["time"])
    if row.get("duration"):
        row["duration"] = normalize_duration_text(row["duration"])

    for key in ["notable_sights", "includes"]:
        if key in row and isinstance(row.get(key), list):
            row[key] = [fix_common_text(item) for item in row[key] if fix_common_text(item)]

    row_type = row.get("effective_type") or row.get("type", "")
    title = row.get("title", "")
    details = row.get("details", "")
    city = row.get("city", "")
    combined_lower = f"{title} {details}".lower()

    if row_type == "Transfer":
        if "self transfer" in combined_lower:
            row["title"] = standardize_self_transfer_title(title, details, city)
        elif "private" in combined_lower:
            row["title"] = standardize_private_transfer_title(title, details, city)
        elif "shuttle" in combined_lower:
            row["title"] = standardize_shuttle_transfer_title(title, details, city)

    if row_type in {"Transport", "Train", "Flight", "Cruise", "Ferry"}:
        row["title"] = create_clean_transport_title(row)

    return row


def extract_detail(text, label):
    """Extract a labelled detail section, matching labels case-insensitively.

    Supplier rows are not consistent about label casing, for example
    ``Notable sights:`` vs ``Notable Sights:``.  The previous exact-string
    extraction missed those sections and let later metadata leak into fields
    such as the meeting point.
    """

    source = str(text or "")
    label_pattern = re.compile(rf"\b{re.escape(label)}\s*:", flags=re.IGNORECASE)
    match = label_pattern.search(source)
    if not match:
        return ""

    after_marker = source[match.end():]
    stop_labels = [re.escape(item) for item in DETAIL_LABELS if item.lower() != str(label).lower()]
    if stop_labels:
        stop_pattern = re.compile(rf"\s+-\s+(?:{'|'.join(stop_labels)})\s*:", flags=re.IGNORECASE)
        stop_match = stop_pattern.search(after_marker)
        if stop_match:
            after_marker = after_marker[:stop_match.start()]

    return after_marker.strip(" -")


def extract_between_markers(text, start_patterns, stop_patterns):
    """
    Extract a section from long supplier-style descriptions.

    Used for colleague paste formats where cells contain blocks like:
    What's included?
    item
    item
    Pick up / meeting point
    address
    """

    if not text:
        return ""

    lowered = text.lower()
    starts = []

    for pattern in start_patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            starts.append(match.end())

    if not starts:
        return ""

    start = min(starts)
    section = text[start:]

    stop_positions = []
    section_lower = section.lower()

    for pattern in stop_patterns:
        match = re.search(pattern, section_lower, flags=re.IGNORECASE)
        if match:
            stop_positions.append(match.start())

    if stop_positions:
        section = section[:min(stop_positions)]

    return section.strip(" :|-\n\r\t")


def clean_title(text):
    """
    Removes labelled detail sections and long supplier text from a title.
    """

    title = clean_space(text)

    # Standard format: "Title - Time: ... - Includes: ..."
    for marker in DETAIL_MARKERS:
        if marker in title:
            title = title.split(marker, 1)[0]

    # Colleague format: "Title | 20:00 | 5 Hrs | Overview..."
    if "|" in title:
        title = title.split("|", 1)[0]

    # Prevent long supplier sections from becoming titles. These markers may
    # appear with or without a preceding dash in real pasted supplier cells.
    for marker in [
        "What's included",
        "What’s included",
        "Included:",
        "Includes:",
        "Overview",
        "What to expect",
        "Pick up / meeting point",
        "Meeting point",
    ]:
        index = title.lower().find(marker.lower())
        if index > 0:
            title = title[:index]

    title = title.strip(" -:|")

    # Remove duplicated city prefix only when the colon is clearly a city prefix.
    # Do not split clock times such as "04:30 PM" in arrival rows.
    if ":" in title and not re.search(r"\b\d{1,2}:\d{2}\b", title):
        possible_city, rest = title.split(":", 1)
        if len(possible_city.strip()) <= 25 and rest.strip() and is_valid_city_value(possible_city):
            title = rest.strip()

    return polish_title(clean_space(title))


def split_comma_list(text, *, protect_compound_phrases=False):
    if not text:
        return []

    if isinstance(text, list):
        return [clean_space(item) for item in text if clean_space(item)]

    text = str(text).replace("\r", "\n")

    # Multiline supplier blocks should normally be one item per line. If a
    # pasted line itself contains several comma-separated inclusions, split that
    # line as well, while later re-merging protected phrases such as
    # "Professional, English-speaking guide".
    if "\n" in text:
        parts = []
        for line in text.splitlines():
            clean_line = clean_space(line.strip("•-* \t"))
            if not clean_line:
                continue
            lower_line = clean_line.lower()
            # Most multiline supplier sections are one inclusion per line, but
            # older compact supplier lines use commas to list separate gear
            # items. Preserve natural single-phrase inclusions that contain
            # commas, especially admission/spa wording like "Unlimited use of
            # steam bath, sauna, and cold lagoon".
            preserve_as_one = lower_line.startswith((
                "unlimited use of ",
                "use of ",
                "access to ",
                "one drink of ",
                "two additional ",
                "boots",
                "gloves",
                "camera assistance",
                "cookies and cake",
                "hot coffee",
                "hot beverages",
            )) or ("coffee" in lower_line and "snack" in lower_line) or ("fish soup" in lower_line and "lunch" in lower_line) or ("thermal suit" in lower_line and "boots" in lower_line)
            if preserve_as_one:
                parts.append(clean_line)
                continue
            comma_parts = [clean_space(item) for item in clean_line.split(",") if clean_space(item)]
            if len(comma_parts) > 1:
                parts.extend(comma_parts)
            else:
                parts.append(clean_line)
    else:
        parts = [clean_space(item) for item in str(text).split(",") if clean_space(item)]

    # Remove section headers that sometimes leak into supplier inclusion lists.
    parts = [
        part for part in parts
        if clean_space(part).lower().strip(':?') not in {
            "what's included",
            "what’s included",
            "includes",
            "included",
        }
    ]

    if not protect_compound_phrases:
        return polish_inclusion_items(parts)

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
        "small-group",
        "small group",
    )

    for part in parts:
        lower = part.lower()

        if merged and (lower.startswith(attach_to_previous_prefixes) or lower.startswith("and ")):
            merged[-1] = f"{merged[-1]}, {part}"
        else:
            merged.append(part)

    return polish_inclusion_items(merged)


def detect_effective_type(item_type, title, details):
    combined = f"{title} {details}".lower().strip()
    normalized_item_type = normalize_type(item_type)

    # Hop-on hop-off / city pass style products are client activities, not
    # transport segments, even if the word "bus" appears in the title.
    if normalized_item_type == "Activity" and any(
        marker in combined
        for marker in ["hop on", "hop-on", "hop off", "hop-off", "24 hrs ticket", "24 hour ticket"]
    ):
        return "Activity"

    if "norway in a nutshell" in combined:
        return "Transport"

    if (
        "flight to" in combined
        or combined.startswith("flight ")
        or re.search(r"\bflight\s*[:|]", combined)
        or re.search(r"\bflight\s+[a-zà-ÿøåäö\s]+\s+to\s+", combined)
    ):
        return "Flight"

    if (
        "train to" in combined
        or "train transfer" in combined
        or "express train" in combined
        or "overnight train" in combined
        or re.search(r"\btrain\s*[:|]", combined)
        or re.search(r"\btrain\s+[a-zà-ÿøåäö\s]+\s+to\s+", combined)
    ):
        return "Train"

    if "cruise to" in combined or "overnight cruise" in combined:
        return "Cruise"

    if "ferry to" in combined:
        return "Ferry"

    # For explicit activity rows, do not downgrade the activity just because the
    # supplier text mentions a bus/coach as part of the experience.
    if normalized_item_type == "Activity":
        return "Activity"

    # Long-distance coach/bus rows should remain arranged transport even when
    # the description also mentions a bus station or resort/accommodation.
    if normalized_item_type == "Transfer" and (
        re.search(r"\b(?:bus|coach)\s*[:|]", combined)
        or "coach transfer" in combined
        or "panorama coach" in combined
        or "panoramic coach" in combined
        or "long distance" in combined and ("coach" in combined or "bus" in combined)
    ) and "private" not in combined:
        return "Transport"

    # Plain private/self-guided/local transfers remain transfers even when the
    # destination text contains "bus station". Long-distance coach/bus rows can
    # still become Transport below.
    if normalized_item_type == "Transfer" and any(
        marker in combined
        for marker in [
            "self transfer", "self-guided transfer", "private",
            "hotel to", "airport to", "station to", "to hotel",
            "to airport", "to station", "accommodation", "bus station", "bustation",
        ]
    ) and "coach transfer to" not in combined and not re.search(r"\b(bus|coach)\s*\d+\b", combined):
        return "Transfer"

    if (
        "coach transfer" in combined
        or combined.startswith("bus")
        or " bus " in f" {combined} "
    ) and "private" not in combined:
        return "Transport"

    return normalized_item_type
