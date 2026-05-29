"""Rental vehicle inclusion summary helpers."""

import re

from text_polish import polish_inclusion_item, polish_title

from itinerary_generation.common import get_row_type
from .inclusion_utils import add_unique, clean, join_detail_parts


def extract_rental_summary(rows: list[dict]) -> list[str]:
    source_rows = [row for row in rows if get_row_type(row) == "Day Overview" and re.search(r"rental\s+(?:vehicle|car|suv)|pick\s*up\s+rental|pickup\s+rental|drop\s+vehicle|return\s+vehicle", f'{row.get("title", "")} {row.get("details", "")}', flags=re.IGNORECASE)]
    examples: list[str] = []
    included: list[str] = []
    has_suv = False
    has_pickup = False
    has_drop = False
    for row in source_rows:
        text = f'{row.get("title", "")}\n{row.get("details", "")}'.replace("|", "\n").replace("✅", "")
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
            if "drop vehicle" in lower or "return vehicle" in lower:
                has_drop = True
            if lower in {"included", "includes"}:
                mode = "included"
                continue
            if lower.startswith("not included"):
                mode = "not_included"
                continue
            if "option" in lower and "similar category" in lower:
                mode = "examples"
                continue
            if mode == "examples" and not re.search(r"option|similar", lower):
                add_unique(examples, polish_title(line))
            elif mode == "included":
                if lower == "automatic":
                    line = "Automatic transmission"
                add_unique(included, polish_inclusion_item(line, "Rental vehicle"))
    items: list[str] = []
    vehicle_label = "Rental SUV" if has_suv else "Rental vehicle"
    if has_pickup:
        if examples:
            add_unique(items, f"{vehicle_label}, such as a {examples[0]} or similar")
        else:
            add_unique(items, f"{vehicle_label} or similar")
    if included:
        detail = join_detail_parts([item.lower() if item != "GPS" else item for item in included]).strip(" .")
        if detail:
            add_unique(items, detail[:1].upper() + detail[1:] + " included")
    if has_drop:
        add_unique(items, "Rental vehicle return at the rental office or airport")
    return items
