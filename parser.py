def extract_detail(text, label):
    """
    Extracts details from text like:
    'Time: 10:30 am - 12:45 pm'
    'Meeting point: Senate Square'
    'Luggage included: 1 x 23 kg check in...'
    """

    marker = f"{label}:"

    if marker not in text:
        return ""

    after_marker = text.split(marker, 1)[1]

    possible_next_markers = [
        " - Time:",
        " - Meeting point:",
        " - End point:",
        " - Includes:",
        " - Notable Sights:",
        " - Schedule:",
        " - Luggage included:",
    ]

    for next_marker in possible_next_markers:
        if next_marker in after_marker:
            after_marker = after_marker.split(next_marker, 1)[0]

    return after_marker.strip(" -")


def clean_title(text):
    """
    Removes detail sections from a title.
    """

    markers = [
        " - Time:",
        " - Meeting point:",
        " - End point:",
        " - Includes:",
        " - Notable Sights:",
        " - Schedule:",
        " - Luggage included:",
    ]

    title = text

    for marker in markers:
        if marker in title:
            title = title.split(marker, 1)[0]

    return title.strip()


def split_comma_list(text):
    """
    Turns comma-separated text into a clean list.
    """

    if not text:
        return []

    if isinstance(text, list):
        return text

    return [item.strip() for item in text.split(",") if item.strip()]


def detect_effective_type(item_type, title, details):
    """
    Detects transport even when the raw type is wrong.
    Example: Activity: Flight to Tromsø should behave as Flight/Transport.
    """

    combined = f"{title} {details}".lower()

    if "flight to" in combined or combined.startswith("flight "):
        return "Flight"

    if "train to" in combined or "train transfer" in combined or "express train" in combined:
        return "Train"

    if "cruise to" in combined or "overnight cruise" in combined:
        return "Cruise"

    if "ferry to" in combined:
        return "Ferry"

    return item_type


def parse_itinerary(raw_text):
    """
    Turns pasted Excel-style itinerary text into structured itinerary rows.
    """

    rows = []

    for line in raw_text.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split("\t")

        row = {
            "raw": line,
            "day": "",
            "type": "",
            "effective_type": "",
            "start_date": "",
            "end_date": "",
            "city": "",
            "title": "",
            "details": "",
            "time": "",
            "meeting_point": "",
            "end_point": "",
            "notable_sights": [],
            "includes": [],
            "luggage_included": "",
        }

        if len(parts) >= 1:
            row["day"] = parts[0].strip()

        if len(parts) >= 2:
            row["type"] = parts[1].strip()

        if len(parts) >= 3:
            row["start_date"] = parts[2].strip()

        if len(parts) >= 4:
            row["end_date"] = parts[3].strip()

        description = parts[-1].strip() if parts else ""

        if ":" in description:
            city, rest = description.split(":", 1)
            row["city"] = city.strip()
            main_text = rest.strip()
        else:
            main_text = description

        row["title"] = clean_title(main_text)
        row["details"] = description
        row["time"] = extract_detail(main_text, "Time")
        row["meeting_point"] = extract_detail(main_text, "Meeting point")
        row["end_point"] = extract_detail(main_text, "End point")
        row["notable_sights"] = split_comma_list(extract_detail(main_text, "Notable Sights"))
        row["includes"] = split_comma_list(extract_detail(main_text, "Includes"))
        row["luggage_included"] = extract_detail(main_text, "Luggage included")

        row["effective_type"] = detect_effective_type(
            row["type"],
            row["title"],
            row["details"],
        )

        rows.append(row)

    return rows