"""Parser list splitting and inclusion-list cleanup."""
import re

from place_aliases import is_known_place

from parser_modules.common import *  # noqa: F401,F403
from parser_modules.time_parsing import normalize_duration_text, normalize_time_text

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
