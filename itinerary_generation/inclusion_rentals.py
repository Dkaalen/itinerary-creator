"""Rental vehicle inclusion summary helpers."""

import re

from text_polish import polish_inclusion_item, polish_title

from itinerary_generation.common import get_row_type
from .inclusion_utils import add_unique, clean, join_detail_parts


_RENTAL_MARKER_RE = re.compile(
    r"\b(?:rental\s+(?:vehicle|car|suv)|car\s+rental|hire\s+car|pick\s*up\s+(?:your\s+)?rental|pickup\s+rental|deliver\s+(?:your\s+)?rental|return\s+(?:your\s+)?rental|drop\s+(?:off\s+)?(?:your\s+)?rental)",
    flags=re.IGNORECASE,
)


def _is_rental_source_row(row: dict) -> bool:
    text = f'{row.get("type", "")} {row.get("effective_type", "")} {row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'
    return get_row_type(row) == "Day Overview" and _RENTAL_MARKER_RE.search(text) or get_row_type(row) == "Car" or bool(_RENTAL_MARKER_RE.search(text))


def _split_inline_includes(text: str) -> list[str]:
    match = re.search(r"\bIncludes?\s*:\s*(.+)$", text, flags=re.IGNORECASE)
    if not match:
        return []
    include_text = re.split(r"\s+-\s+(?:Description|Not included|Excludes?)\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
    items = []
    for part in re.split(r",|;|\n", include_text):
        item = clean(part).strip(" .:-")
        if not item:
            continue
        if item.lower() in {"cancellation fee"}:
            continue
        if item.lower() == "vat":
            item = "VAT"
        add_unique(items, polish_inclusion_item(item, "Rental vehicle"))
    return items


def _extract_vehicle_example(text: str) -> str:
    patterns = [
        r"rental\s+car\s+at\s+.+?\s+-\s*(.+?)(?:\s+-\s*Includes?\s*:|$)",
        r"pick\s*up\s+(?:your\s+)?rental\s+car\s+.+?\s+-\s*(.+?)(?:\s+-\s*Includes?\s*:|$)",
        r"rental\s+(?:vehicle|suv)\s+[-:]\s*(.+?)(?:\s+-\s*Includes?\s*:|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = clean(match.group(1)).strip(" .:-")
            if value and not re.search(r"\b(?:includes?|airport|office|charge|waiver|tax|licence|protection)\b", value, flags=re.IGNORECASE):
                return polish_title(value)
    return ""


def extract_rental_summary(rows: list[dict]) -> list[str]:
    source_rows = [row for row in rows if _is_rental_source_row(row)]
    examples: list[str] = []
    included: list[str] = []
    has_suv = False
    has_pickup = False
    has_drop = False
    examples_are_or_similar = False

    for row in source_rows:
        text = f'{row.get("title", "")}\n{row.get("original_title", "")}\n{row.get("details", "")}'.replace("|", "\n").replace("✅", "")
        lower_text = text.lower()
        if "suv" in lower_text:
            has_suv = True
        if re.search(r"\b(?:pick\s*up|pickup)\b", lower_text):
            has_pickup = True
        if re.search(r"\b(?:deliver|return|drop(?:\s*off)?)\b", lower_text):
            has_drop = True

        example = _extract_vehicle_example(text)
        if example:
            add_unique(examples, example)

        for item in _split_inline_includes(text):
            add_unique(included, item)

        mode = "pickup"
        for raw in text.splitlines():
            line = clean(raw).strip(" •-*:")
            if not line:
                continue
            lower = line.lower()
            if "rental suv" in lower or "suv" in lower:
                has_suv = True
            if "pick" in lower and "rental" in lower:
                has_pickup = True
            if "drop vehicle" in lower or "return vehicle" in lower or "deliver" in lower and "rental" in lower:
                has_drop = True
            if lower in {"included", "includes"}:
                mode = "included"
                continue
            if lower.startswith("not included"):
                mode = "not_included"
                continue
            if "option" in lower and "similar category" in lower:
                examples_are_or_similar = True
                mode = "examples"
                continue
            if mode == "examples" and not re.search(r"option|similar", lower):
                add_unique(examples, polish_title(line))
            elif mode == "included":
                if lower == "automatic":
                    line = "Automatic transmission"
                if lower != "cancellation fee":
                    add_unique(included, polish_inclusion_item(line, "Rental vehicle"))

    items: list[str] = []
    vehicle_label = "Rental SUV" if has_suv else "Rental car"
    if has_pickup or examples or included:
        if examples:
            article = "" if examples[0].lower().startswith(("a ", "an ", "the ")) else "a "
            suffix = " or similar" if examples_are_or_similar and "or similar" not in examples[0].lower() else ""
            add_unique(items, f"{vehicle_label}, such as {article}{examples[0]}{suffix}")
        else:
            add_unique(items, f"{vehicle_label} or similar")
    if included:
        detail = join_detail_parts([item.lower() if item != "VAT" and item != "GPS" else item for item in included]).strip(" .")
        if detail:
            add_unique(items, detail[:1].upper() + detail[1:] + " included")
    if has_drop:
        add_unique(items, "Rental car return at the airport rental office")
    return items
