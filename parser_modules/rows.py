import hashlib

from parser_modules.common import *  # noqa: F401,F403


def is_trailing_status_cell(value):
    """Return True for stray spreadsheet markers that are not itinerary content."""
    text = clean_space(value).strip('"\' \t')
    return text.lower() in {"", "x", "yes", "no", "true", "false", "-", "—"}

def preprocess_raw_rows(raw_text):
    """
    Rebuild rows when Excel cells contain line breaks.

    A new row starts when one of the first few tab-separated cells contains
    "Day X". Lines that do not start a row are appended to the previous row.

    Optional add-on sections are preserved and marked instead of being appended
    to the previous real itinerary row. This lets the app render optional add-ons
    in their own section without polluting the main itinerary, destination list,
    day count, or final-day logic.
    """

    rows = []
    current = ""
    optional_mode = False

    def flush_current():
        nonlocal current
        if current.strip():
            rows.append(current)
        current = ""

    for raw_line in raw_text.splitlines():
        if not raw_line.strip():
            continue

        parts = raw_line.split("\t")
        starts_new_row = any(looks_like_day(part) for part in parts[:4])

        if not starts_new_row and is_optional_addon_header(raw_line):
            flush_current()
            optional_mode = True
            continue

        if starts_new_row:
            flush_current()
            prefix = "__OPTIONAL__\t" if optional_mode else "__MAIN__\t"
            current = prefix + raw_line
        else:
            if current:
                current += "\n" + raw_line
            else:
                prefix = "__OPTIONAL__\t" if optional_mode else "__MAIN__\t"
                current = prefix + raw_line

    flush_current()

    return rows

def find_day_index(parts):
    for index, part in enumerate(parts[:5]):
        if looks_like_day(part):
            return index

    return None


def find_description_cell(parts):
    """
    Return the rightmost meaningful content cell as the description.

    Some exported spreadsheet rows end with status cells such as ``x`` or a
    stray quote after the real description. Those markers must not replace the
    supplier text or cause a valid activity row to be skipped.
    """

    for part in reversed(parts):
        raw_value = str(part or "").strip()

        if is_trailing_status_cell(raw_value):
            continue

        value = raw_value.strip('"')
        if value.strip():
            return value.strip()

    return ""


def find_city_cell(parts, description_index):
    """
    Finds a separate city column when the pasted row uses one.

    In the user's format, city is usually embedded in "City: description".
    In the colleague format, city is usually the non-empty cell before the
    description.
    """

    for index in range(description_index - 1, -1, -1):
        value = clean_space(parts[index]).strip('"')

        if not value or is_trailing_status_cell(value):
            continue

        if is_valid_city_value(value):
            return value

    return ""


def get_description_index(parts):
    for index in range(len(parts) - 1, -1, -1):
        if clean_space(parts[index]) and not is_trailing_status_cell(parts[index]):
            return index

    return -1


def make_row_id(day, item_type, start_date, end_date, description):
    source = "|".join([
        day.strip().lower(),
        item_type.strip().lower(),
        start_date.strip().lower(),
        end_date.strip().lower(),
        description.strip().lower(),
    ])

    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]
