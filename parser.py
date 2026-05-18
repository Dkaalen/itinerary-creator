def extract_detail(text, label):
    """
    Extracts details from text like:
    'Time: 10:30 am - 12:45 pm'
    'Meeting point: Senate Square'
    'Includes: Guide, Liability Insurance'
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
    ]

    title = text

    for marker in markers:
        if marker in title:
            title = title.split(marker, 1)[0]

    return title.strip()


def split_includes(includes_text):
    """
    Turns comma-separated includes into a clean list.
    """

    if not includes_text:
        return []

    return [item.strip() for item in includes_text.split(",") if item.strip()]


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
            "start_date": "",
            "end_date": "",
            "city": "",
            "title": "",
            "details": "",
            "time": "",
            "meeting_point": "",
            "end_point": "",
            "notable_sights": "",
            "includes": [],
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
        row["notable_sights"] = extract_detail(main_text, "Notable Sights")
        row["includes"] = split_includes(extract_detail(main_text, "Includes"))

        rows.append(row)

    return rows