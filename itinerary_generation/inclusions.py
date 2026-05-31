from text_polish import polish_inclusion_item, polish_title

from itinerary_generation.common import (
    TRANSPORT_TYPES,
    add_unique,
    get_day_count,
    get_row_type,
    main_rows_only,
    is_self_arranged,
)
from itinerary_generation.transport import (
    get_transfer_travel_title,
    is_route_transfer,
)
from itinerary_generation.titles import create_client_activity_title


def sentence_case_transport_title(title):
    title = str(title or "").strip()
    replacements = {
        "Coach Transfer": "Coach transfer",
        "Tickets Included": "tickets included",
        "Tickets included": "tickets included",
        "Luggage porter service included": "luggage porter service",
    }
    for old, new in replacements.items():
        title = title.replace(old, new)
    return title


def clean_include_item(value, context_title=""):
    """Normalize inclusion bullet wording for both summaries and day blocks."""
    item = polish_inclusion_item(value, context_title)
    lower = item.lower()
    context_lower = str(context_title or "").lower()

    if lower in {"tickets included", "ticket included"}:
        if "coach" in context_lower or "bus" in context_lower:
            return "Coach ticket"
        if "train" in context_lower:
            return "Train ticket"
        if "ferry" in context_lower or "cruise" in context_lower:
            return "Ticket"
        return "Ticket"

    if lower == "luggage porter service included":
        return "Luggage porter service"

    if lower.endswith(" included") and len(item.split()) <= 5:
        return item[:-9].strip().capitalize()

    item = item.replace("Tickets included", "tickets included")
    item = item.replace("Luggage porter service included", "luggage porter service")
    item = item.replace("  ", " ")
    return polish_inclusion_item(item, context_title)


def format_transport_inclusion(title, includes=None, luggage=""):
    title = polish_title(sentence_case_transport_title(title))
    includes = [clean_include_item(item, title) for item in (includes or []) if clean_include_item(item, title)]
    luggage = clean_include_item(luggage, title)

    if luggage:
        return f"{title}, including {luggage}"

    if includes:
        include_text = ", ".join(includes)
        if len(includes) == 1 and "included" in include_text.lower():
            return f"{title}, {include_text}"
        return f"{title}, including {include_text}"

    return title


def create_whats_included(parsed_rows, grouped_days):
    parsed_rows = main_rows_only(parsed_rows)
    included = []

    hotel_rows = [row for row in parsed_rows if get_row_type(row) == "Hotel"]
    transfer_rows = [row for row in parsed_rows if get_row_type(row) == "Transfer"]
    transport_rows = [row for row in parsed_rows if get_row_type(row) in TRANSPORT_TYPES]
    activity_rows = [row for row in parsed_rows if get_row_type(row) == "Activity"]

    nights = sum(int(str(row.get("hotel_nights", "") or "0")) for row in hotel_rows if str(row.get("hotel_nights", "") or "").strip().isdigit())
    if nights <= 0:
        nights = max(get_day_count(grouped_days) - 1, 0)

    if hotel_rows:
        night_word = "night" if nights == 1 else "nights"
        add_unique(included, f"{nights} {night_word} as specified")
        add_unique(included, "Accommodation as listed in the itinerary")

    if any("breakfast" in row.get("details", "").lower() or "brekafast" in row.get("details", "").lower() for row in hotel_rows):
        add_unique(included, "Breakfast included where specified")

    has_private_transfer = any("private transfer" in row.get("details", "").lower() or "private" in row.get("title", "").lower() for row in transfer_rows)

    if has_private_transfer:
        add_unique(included, "Private transfers as listed in the itinerary")

    for row in transport_rows:
        if is_self_arranged(row):
            continue

        title = row.get("title", "").strip()
        luggage = row.get("luggage_included", "").strip()
        includes = row.get("includes", [])
        add_unique(included, format_transport_inclusion(title, includes, luggage))

    for row in transfer_rows:
        if is_route_transfer(row) and not is_self_arranged(row):
            add_unique(included, get_transfer_travel_title(row))

    for row in activity_rows:
        title = create_client_activity_title(row) or row.get("title", "").strip()

        if title:
            add_unique(included, title)

    return included


def create_whats_not_included(parsed_rows=None):
    items = [
        "International flights unless specifically listed",
        "Meals unless specifically stated",
        "Drinks unless specifically stated",
        "Porterage unless specified",
        "Self transfers and self-arranged travel costs unless specifically stated",
        "Travel insurance",
        "Optional extras and personal expenses",
        "City taxes or local fees, where applicable",
    ]
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in (parsed_rows or [])).lower()
    if "self arranged" in text or "self-arranged" in text or "self arrnaged" in text or "cost not included" in text or "price not included" in text:
        note = "Self-arranged flights or transport listed in the itinerary, unless specifically stated as included"
        if note not in items:
            items.insert(1, note)
    if "optional addon" in text or "optional add-on" in text or "optional add on" in text:
        note = "Optional add-ons and experiences unless specifically selected"
        if note not in items:
            items.insert(1, note)
    if "excludes" in text or "not included" in text or "to be bought on site" in text:
        note = "Tickets or services marked as excluded or to be bought on site"
        if note not in items:
            items.insert(1, note)
    return items


def create_final_note(parsed_rows, grouped_days):
    # Kept for backward compatibility with older imports.
    return ""
