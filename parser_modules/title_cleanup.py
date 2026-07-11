"""Parser title cleanup and title/prose splitting."""
import re

from place_aliases import is_known_place

from parser_modules.common import *  # noqa: F401,F403
from parser_modules.time_parsing import normalize_duration_text, normalize_time_text
from parser_modules.title_prose_boundaries import (
    extract_supplier_prose_product_name as _supplier_prose_product_name,
    split_long_title_from_prose as _split_long_title_from_prose,
)

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
    title = re.sub(r"^\s*detailed\s+itinerary(?:\s+day\s+\d+)?\s*[:,-]?\s*", "", title, flags=re.IGNORECASE)
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
        if re.search(r"(?:^|[-|])\s*(?:time|driving\s+time|duration|highlights?|stops?|includes?|meeting\s+point)\b", possible_city_clean, flags=re.IGNORECASE):
            break
        if _looks_like_product_title(possible_city_clean) and not is_known_place(possible_city_clean):
            break
        if len(possible_city_clean) <= 35 and rest_clean and is_valid_city_value(possible_city_clean):
            title = rest_clean
            continue
        break
    return title




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
