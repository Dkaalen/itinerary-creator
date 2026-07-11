"""Raw-row context helpers used before parser row enrichment."""

import re

from parser_modules.common import clean_space, fix_common_text, is_valid_city_value, normalize_type
from parser_modules.rows import find_city_cell


def fix_common_text_for_row(value, item_type):
    """Apply broad cleanup without rewriting supplier-owned hotel names."""

    if normalize_type(item_type) != "Hotel":
        return fix_common_text(value)

    protected = re.sub(r"\bAurora\b", "__HOTEL_AURORA__", str(value or ""), flags=re.IGNORECASE)
    cleaned = fix_common_text(protected)
    return cleaned.replace("__HOTEL_AURORA__", "Aurora")


def fixed_format_city_only_description(parts, description_index, item_type):
    """Detect the app's fixed Excel paste shape when Details is blank."""

    if len(parts) <= 10 or description_index != 9:
        return "", ""
    city = clean_space(parts[9]).strip('"')
    trailing_details = clean_space(parts[10]).strip('"')
    if trailing_details or not is_valid_city_value(city):
        return "", ""

    normalized_type = normalize_type(item_type)
    fallback_titles = {
        "Activity": f"Time in {city}",
        "Transfer": f"Transfer in {city}",
        "Transport": f"Transport in {city}",
        "Train": f"Train in {city}",
        "Flight": f"Flight in {city}",
        "Cruise": f"Cruise in {city}",
        "Ferry": f"Ferry in {city}",
        "Hotel": f"Accommodation in {city}",
        "Leisure": f"Leisure time in {city}",
    }
    return city, fallback_titles.get(normalized_type, city)



def extract_city_and_description(parts, description_index, item_type, description):
    """Resolve a separate city cell and fixed-format blank-details fallback."""

    separate_city = find_city_cell(parts, description_index)
    city_only_cell, city_only_description = fixed_format_city_only_description(parts, description_index, item_type)
    if city_only_cell and city_only_description:
        return city_only_cell, city_only_description
    return separate_city, description

def strip_matching_type_prefix(main_text, item_type):
    """Remove duplicated administrative row-type prefixes from descriptions."""

    type_prefix = re.match(
        r"^\s*(Activity|Transfer|Hotel|Train|Flight|Cruise|Ferry|Transport|Leisure|Arrival|Departure)\s*:\s*(.+)$",
        str(main_text or ""),
        flags=re.IGNORECASE,
    )
    if type_prefix and type_prefix.group(1).lower() == normalize_type(item_type).lower():
        return type_prefix.group(2).strip()
    return main_text


# Backwards-compatible aliases for tests or legacy imports.
_fix_common_text_for_row = fix_common_text_for_row
_fixed_format_city_only_description = fixed_format_city_only_description
