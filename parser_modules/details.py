import re

from place_aliases import is_known_place

from parser_modules.common import *  # noqa: F401,F403
from parser_modules.time_parsing import normalize_duration_text, normalize_time_text


def _fix_common_text_for_context(value, *, row_type="", field=""):
    """Run parser cleanup while preserving supplier-owned hotel text."""

    if row_type == "Hotel" and field in {"title", "details", "hotel_name"}:
        protected = re.sub(r"\bAurora\b", "__HOTEL_AURORA__", str(value or ""), flags=re.IGNORECASE)
        cleaned = fix_common_text(protected)
        return polish_hotel_name(cleaned.replace("__HOTEL_AURORA__", "Aurora")) if field in {"title", "hotel_name"} else cleaned.replace("__HOTEL_AURORA__", "Aurora")
    return fix_common_text(value)

def standardize_row_text(row):
    """Applies client-facing cleanup after row parsing and effective type detection."""

    # Do not run the broad client-text polish on parsed time values.
    # Time fields are normalized by the dedicated time parser; broad punctuation
    # polish can corrupt clock syntax if it ever changes colon spacing.
    row_type = row.get("effective_type") or row.get("type", "")
    for key in ["city", "title", "details", "meeting_point", "end_point", "luggage_included", "hotel_name", "room_category", "meal_plan"]:
        if key in row and row.get(key):
            row[key] = _fix_common_text_for_context(row[key], row_type=row_type, field=key)

    if row.get("time"):
        row["time"] = normalize_time_text(row["time"])
    if row.get("duration"):
        row["duration"] = normalize_duration_text(row["duration"])

    for key in ["notable_sights", "includes"]:
        if key in row and isinstance(row.get(key), list):
            row[key] = [fix_common_text(item) for item in row[key] if fix_common_text(item)]

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

    if row_type in {"Arrival", "Departure"} and any(marker in combined_lower for marker in ["private", "shuttle", "self transfer"]):
        if "self transfer" in combined_lower:
            row["title"] = standardize_self_transfer_title(title, details, city)
        elif "private" in combined_lower:
            row["title"] = standardize_private_transfer_title(title, details, city)
        elif "shuttle" in combined_lower:
            row["title"] = standardize_shuttle_transfer_title(title, details, city)

    if row_type in {"Transport", "Train", "Flight", "Cruise", "Ferry"}:
        row["title"] = create_clean_transport_title(row)

    return row


def _looks_like_cruise_experience_text(text: str) -> bool:
    """Return True when cruise wording describes a bookable experience.

    Supplier activity rows often contain route-shaped wording such as
    ``fjord cruise to Mostraumen``.  That should stay an Activity unless the
    row is clearly an overnight/point-to-point cruise or ferry transfer.
    """

    lower = str(text or "").lower()
    if not lower or "cruise" not in lower:
        return False

    if re.search(r"\b(?:overnight|night|coastal|atlantic ocean)\s+cruise\b", lower):
        return False
    if re.search(r"\bcruise\s+(?:from\s+)?[a-zà-ÿøåäö .'-]+\s+to\s+[a-zà-ÿøåäö .'-]+\b", lower) and not any(
        marker in lower
        for marker in ["round-trip", "round trip", "return", "day trip", "sightseeing", "fjord", "canal", "archipelago"]
    ):
        return False

    experience_markers = [
        "fjord cruise",
        "sightseeing cruise",
        "cruise day trip",
        "day cruise",
        "canal cruise",
        "archipelago cruise",
        "wildlife cruise",
        "northern lights cruise",
        "icebreaker cruise",
        "dinner cruise",
        "private cruise",
        "boat tour",
        "catamaran",
        "rib safari",
        "sea eagle",
        "oslofjord",
        "oslo fjord",
        "nærøyfjord",
        "naeroyfjord",
        "mostraumen",
        "geirangerfjord",
        "geiranger fjord",
        "trollfjord",
    ]
    if any(marker in lower for marker in experience_markers):
        return True

    # Labelled activity metadata strongly implies the cruise is an excursion,
    # not a location-changing transport row.
    return bool(re.search(r"\b(?:time|duration|meeting point|includes?|description)\s*:", lower))


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
    stop_labels.extend([
        r"what[’']?s\s+included",
        r"what\s+is\s+included",
        r"what\s+to\s+expect",
        r"overview",
        r"please\s+note",
        r"important\s+information",
        r"pick[-\s]*up\s*/\s*meeting\s*point",
        r"meeting\s+point",
    ])
    if stop_labels:
        # Stop on both dash-separated metadata (" - Includes:") and supplier
        # block labels on their own line or after a pasted sentence.  Without
        # this, labels such as "What's included?" can leak into meeting points.
        stop_pattern = re.compile(
            rf"(?:\s+-\s+|\n+\s*|\s{{2,}})(?:{'|'.join(stop_labels)})\s*(?::|\?|(?=\s|[A-ZÀ-ÖØ-Þ]))",
            flags=re.IGNORECASE,
        )
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


def _best_title_source(text):
    """Return the most title-like part of messy supplier text.

    Large calculator cells often paste a compact title on the first line and the
    full supplier description below it.  Using the whole cell as the title makes
    activity headings explode in the itinerary and PDF.
    """

    source = str(text or "").strip()
    lines = [clean_space(line) for line in source.replace("\r", "\n").split("\n") if clean_space(line)]
    if not lines:
        return clean_space(source)

    first = lines[0]
    first_lower = first.lower().strip(" :-")
    if first_lower not in {
        "overview",
        "what's included",
        "what’s included",
        "what to expect",
        "meeting point",
        "pick up / meeting point",
    } and len(first) <= 160:
        return first

    return clean_space(source)


def _strip_admin_title_prefixes(title):
    title = re.sub(r"^\s*(?:optional|optinal|optional\s*/\s*recommended|optional\s+recommended|add[-\s]*on\s+optional)\s*[:,-]\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*day\s+\d+\s*[:,-]\s*", "", title, flags=re.IGNORECASE)
    return title.strip()


_PRODUCT_TITLE_WORDS = re.compile(
    r"\b(?:tour|cruise|safari|experience|ticket|tickets|cable\s+car|museum|sauna|sledding|snowmobil|"
    r"hike|walking|excursion|show|dinner|fjord|lagoon|village|package|holiday|rental|transfer)\b",
    flags=re.IGNORECASE,
)


def _looks_like_product_title(value):
    return bool(_PRODUCT_TITLE_WORDS.search(clean_space(value)))


def _strip_repeated_city_prefix(title):
    # Remove one or two leading city prefixes, e.g.
    # "Stockholm: Stockholm Archipelago Dinner Cruise".
    # Keep supplier/product prefixes such as "Fjellheisen Cable Car:" because
    # those are often the best available activity title, not a city.
    for _ in range(2):
        if ":" not in title:
            break
        possible_city, rest = title.split(":", 1)
        if re.search(r"\b\d{1,2}:\d{2}\b", possible_city):
            break
        possible_city_clean = clean_space(possible_city)
        rest_clean = clean_space(rest)
        if "|" in possible_city_clean or re.search(r"\d", possible_city_clean):
            break
        # Labelled activity metadata is not a city prefix. Without this guard,
        # "South Coast Adventure - Time: 08:00..." is split at the Time colon
        # and the title degrades to the clock value.
        if re.search(r"(?:^|[-|])\s*(?:time|duration|highlights?|stops?|includes?|meeting\s+point)\b", possible_city_clean, flags=re.IGNORECASE):
            break
        if _looks_like_product_title(possible_city_clean) and not is_known_place(possible_city_clean):
            break
        if len(possible_city_clean) <= 35 and rest_clean and is_valid_city_value(possible_city_clean):
            title = rest_clean
            continue
        break
    return title


def _split_long_title_from_prose(title):
    """Keep headings compact when supplier body text follows the title."""

    source = clean_space(title)
    source = re.split(
        r"\s*,?\s*\d{1,2}[:.]\s*\d{2}\s+(?:duration|time)\b",
        source,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" -:|,.")
    if len(source) <= 95 and not re.search(r"[.!?]", source):
        return source

    # Common day-overview/activity patterns where a heading is followed by prose.
    prose_starts = [
        r"\s+Make your way\b",
        r"\s+The day starts\b",
        r"\s+The journey continues\b",
        r"\s+The scenery continues\b",
        r"\s+This day is filled\b",
        r"\s+We will start\b",
        r"\s+On this,? our final day\b",
        r"\s+Your journey begins\b",
        r"\s+Your next destination\b",
        r"\s+Prepare to explore\b",
        r"\s+You will visit\b",
        r"\s+The first stop\b",
        r"\s+Embark on\b",
        r"\s+After (?:a |enjoying )?(?:delicious )?breakfast\b",
        r"\s+Start your day\b",
        r"\s+Today'?s journey\b",
        r"\s+On this day\b",
        r"\s+You(?:'|’)ll\b",
        r"\s+You will\b",
        r"\s+A\s+\d{2,4}m\b",
        r"\s+Seljalandsfoss\s*:\b",
        r"\s+Bring a raincoat\b",
        r"\s+Our adventure\b",
        r"\s+the adventure begins\b",
    ]
    for pattern in prose_starts:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match and match.start() >= 8:
            return source[:match.start()].strip(" -:|,.")

    source = re.split(
        r"\s+-\s+(?:[A-Za-zÀ-ÿøØåÅäÄöÖ\s]+\s+)?(?:port\s+)?transfers?\s+included\b|\s+-\s+self[-\s]*guided\b|\s+○\s+",
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

    # Product metadata after a colon often introduces descriptive text rather
    # than a better title: "Cable Car: Tickets Included: Enjoy the view...".
    if ":" in source:
        left, right = source.split(":", 1)
        left = clean_space(left)
        right = clean_space(right)
        if (
            5 <= len(left) <= 70
            and not re.search(r"\d\s*$", left)
            and (
                re.search(r"\b(?:ticket|tickets|included|round trip|admission)\b", right, flags=re.IGNORECASE)
                or re.search(r"[.!?]", right)
                or len(right.split()) >= 10
            )
        ):
            return left

    # Very long comma clauses usually represent extras/notes, not the heading.
    source = re.split(
        r",\s+(?:shared|includes?|with|including|incl\.?|and\s+with|free\s+time|transfer(?:s)?|return\s+transfer)\b",
        source,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    # As a last resort, stop after the first sentence when the rest is prose.
    # Keep product abbreviations such as "incl. Lunch" intact.
    protected_source = re.sub(r"\bincl\.", "incl§", source, flags=re.IGNORECASE)
    sentence = re.split(r"(?<=[.!?])\s+", protected_source, maxsplit=1)[0].replace("incl§", "incl.")
    if len(sentence) >= 8 and len(sentence) < len(source):
        return sentence.strip(" -:|,.")

    return source.strip(" -:|,.")


def clean_title(text):
    """
    Removes labelled detail sections and long supplier text from a title.
    """

    title = clean_space(_best_title_source(text))
    had_day_heading = bool(re.search(r"(?:^|:\s*)day\s+\d+\s*[:,-]", title, flags=re.IGNORECASE))
    title = _strip_admin_title_prefixes(title)
    title = _strip_repeated_city_prefix(title)
    title = _strip_admin_title_prefixes(title)

    # Rows such as "Rovaniemi: | Lakeside Sauna Experience | 10:00..." become
    # leading-pipe titles after the city prefix is removed.  Pick the first
    # non-empty pipe segment instead of returning a blank title.
    if "|" in title:
        pipe_parts = [clean_space(part) for part in title.split("|") if clean_space(part)]
        if pipe_parts:
            title = pipe_parts[0]

    # Supplier rows sometimes append a clock range and then prose to the product
    # heading: "Dinner Cruise (19:00 - 22:00) incl. dinner...". Keep the product
    # name as the title; time extraction handles the clock separately.
    title = re.split(r"\s*\(\s*\d{1,2}[:.]\s*\d{2}\s*(?:-|–|—|to)\s*\d{1,2}[:.]\s*\d{2}.*$", title, maxsplit=1, flags=re.IGNORECASE)[0]
    title = re.split(r"\s+\d{1,2}[:.]\s*\d{2}\s*(?:-|–|—|to)\s*\d{1,2}[:.]\s*\d{2}\b.*$", title, maxsplit=1, flags=re.IGNORECASE)[0]

    # Standard format: "Title - Time: ... - Includes: ..."
    for marker in DETAIL_MARKERS:
        if marker in title:
            title = title.split(marker, 1)[0]

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
        "Pick-up / meeting point",
        "Meeting point",
    ]:
        index = title.lower().find(marker.lower())
        if index > 0:
            title = title[:index]

    title = _strip_admin_title_prefixes(title.strip(" -:|"))
    title = _strip_repeated_city_prefix(title)
    title = _strip_admin_title_prefixes(title)

    if had_day_heading and " - " in title:
        title = title.split(" - ", 1)[0]

    title = _split_long_title_from_prose(title)

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

    # Stegastein electric minibus is a sightseeing activity from Flåm, not a
    # route transfer, even though the supplier wording contains minibus/bus.
    if normalized_item_type == "Activity" and "stegastein" in combined and any(marker in combined for marker in ["electric minibus", "electric bus", "viewpoint", "sightseeing tour"]):
        return "Activity"

    # Overnight/night-train rows are arranged rail even when the cabin text
    # contains words such as "private sleeper compartment". Detect them before
    # local/private-transfer protection.
    if normalized_item_type == "Transfer" and re.search(r"\b(?:overnight|night)\s+train\b", combined, flags=re.IGNORECASE):
        return "Train"

    # Local/private/self transfers must stay transfers even when the terminal
    # contains words like Train Station. Run this before generic train/flight
    # detection so "Self transfer to Bergen Train Station" cannot become a
    # fake train route such as "Train to Bergen".
    if normalized_item_type == "Transfer" and any(
        marker in combined
        for marker in [
            "self transfer", "self-arranged transfer", "self-guided transfer", "private",
            "hotel to", "airport to", "station to", "to hotel", "to airport",
            "to station", "to railway station", "to train station", "accommodation",
            "bus station", "bustation",
        ]
    ) and "coach transfer to" not in combined and not re.search(r"\b(bus|coach)\s*\d+\b", combined):
        return "Transfer"

    # Accommodation-relocation rows occasionally land in the Activity column.
    # Treat explicit transfer-to-igloo/stay snippets as transfer logistics so
    # the accommodation can lead the day title instead of becoming an activity.
    if normalized_item_type == "Activity" and re.search(r"\btransfer\s+to\s+(?:glass\s+)?igloo\s+stay\b|\btransfer\s+to\s+[^.]{0,40}stay\b", combined, flags=re.IGNORECASE):
        return "Transfer"

    # Attraction/ticket products can include shuttle/return-transfer logistics.
    # Keep the product as an activity unless the row is clearly a pure route.
    if normalized_item_type == "Activity" and any(
        marker in combined
        for marker in ["blue lagoon", "comfort ticket", "admission", "entry ticket", "return transfer"]
    ) and any(marker in combined for marker in ["overview", "what's included", "what to expect", "ticket", "admission", "experience"]):
        return "Activity"

    # Tallinn day excursions use ferry tickets as logistics, but the row is the
    # day trip/activity, not a ferry transfer.
    if normalized_item_type == "Activity" and "tallinn" in combined and any(
        marker in combined for marker in ["excursion", "guided tour", "self guided", "old town"]
    ):
        return "Activity"

    if "norway in a nutshell" in combined:
        return "Transport"

    if normalized_item_type == "Activity" and _looks_like_cruise_experience_text(combined):
        return "Activity"

    route_mode_match = re.search(r"\b[a-zà-ÿøåäö .'-]+\s+to\s+[a-zà-ÿøåäö .'-]+\s+(train|flight|cruise|ferry|coach|bus)\b", combined)
    if route_mode_match and normalized_item_type in {"Transfer", "Transport", "Activity"} and "private" not in combined:
        mode = route_mode_match.group(1)
        if mode == "train":
            return "Train"
        if mode == "flight":
            return "Flight"
        if mode in {"cruise", "ferry"}:
            return "Cruise" if mode == "cruise" else "Ferry"
        return "Transport"

    if re.search(r"\b(?:day\s+|overnight\s+)?train\b[^\n|]{0,40}\b[a-zà-ÿøåäö .'-]+\s+-\s+[a-zà-ÿøåäö .'-]+", combined, flags=re.IGNORECASE):
        return "Train"

    if re.search(r"\bflight\b[^\n|]{0,40}\b[a-zà-ÿøåäö .'-]+\s+-\s+[a-zà-ÿøåäö .'-]+", combined, flags=re.IGNORECASE):
        return "Flight"

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
