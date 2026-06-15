"""Structured "what's not included" list helpers.

Exclusions are generated from commercial row status rather than from preview or
PDF presentation code. Keeping this isolated makes optional/self-arranged rules
less likely to leak into inclusion rendering.
"""

import re

from text_polish import polish_client_text, polish_title
from itinerary_generation.client_sanitizer import sanitize_client_text

from itinerary_generation.common import (
    add_unique,
    get_row_type,
    main_rows_only,
    optional_rows_only,
    is_optional_row,
    is_self_arranged,
)
from itinerary_generation.date_formatting import format_client_date
from itinerary_generation.titles import create_client_activity_title
from itinerary_generation.transport_safety import split_self_transfer_notes
from itinerary_generation.transport_domain.exclusions import (
    is_flight_row as _transport_is_flight_row,
    is_self_transfer_row as _transport_is_self_transfer_row,
    is_transport_row as _transport_is_transport_row,
    row_search_text as _transport_row_search_text,
    self_arranged_flight_notice as _transport_self_arranged_flight_notice,
    self_transfer_exclusion_title as _transport_self_transfer_exclusion_title,
    transport_commercial_title as _transport_commercial_title,
)


DEFAULT_WHATS_NOT_INCLUDED_ITEMS = [
    "International flights unless specifically listed",
    "Meals unless specifically stated",
    "Drinks unless specifically stated",
    "Porterage unless specified",
    "Self transfers and self-arranged travel costs unless specifically stated",
    "Travel insurance",
    "Optional extras and personal expenses",
    "Optional experiences unless specifically confirmed",
    "City taxes or local fees, where applicable",
]


EXCLUSION_SECTION_ORDER = [
    ("self_arranged_flights", "Self-arranged flights"),
    ("self_transfers", "Self transfers"),
    ("optional_experiences", "Optional experiences"),
    ("optional_transfers", "Optional transfers"),
    ("optional_hotels", "Optional hotels/add-ons"),
    ("costs_not_included", "Activity-specific exclusions"),
]



def _row_id(row, fallback_index=0):
    value = str((row or {}).get("row_id") or "").strip()
    if value:
        return value
    return f"generated-row-{fallback_index}"


def _structured_item(label, row=None, row_index=0):
    text = str(label or "").strip()
    if not text:
        return None
    source_ids = []
    if row is not None:
        row_id = _row_id(row, row_index)
        if row_id:
            source_ids.append(row_id)
    return {"label": text, "source_row_ids": source_ids}


def _split_exclusion_phrases(value: str) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\bfood\s+and\s+drinks\s+are\s+excluded\b", "Food and drinks", text, flags=re.IGNORECASE)
    parts: list[str] = []
    for line in text.splitlines():
        clean_line = line.strip(" •-*\t:.")
        if not clean_line:
            continue
        for part in re.split(r",\s*", clean_line):
            item = part.strip(" •-*\t:.")
            if item:
                parts.append(item)
    cleaned: list[str] = []
    for item in parts:
        lower = item.lower().strip(" .:")
        if not lower or lower in {"not included", "not included?", "excluded", "what's included", "what’s included"}:
            continue
        item = re.sub(r"^(?:not\s+included|excluded)\s*:?\s*", "", item, flags=re.IGNORECASE).strip(" .:")
        item = re.sub(r"\bdrop\s+to\s+hotel\b", "hotel drop-off", item, flags=re.IGNORECASE)
        item = re.sub(r"\btransportation\s+to\s+meeting\s+point\b", "transport to the meeting point", item, flags=re.IGNORECASE)
        item = re.sub(r"\bfood\s+and\s+drinks\s+are\s+excluded\b", "food and drinks", item, flags=re.IGNORECASE)
        item = sanitize_client_text(polish_client_text(item)).strip(" .:")
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _row_specific_not_included_items(row) -> list[str]:
    source = "\n".join(
        str(row.get(key, "") or "")
        for key in ["details", "original_title", "title"]
        if str(row.get(key, "") or "").strip()
    )
    direct_items: list[str] = []
    if re.search(r"\bwithout\s+meals?\b", source, flags=re.IGNORECASE):
        direct_items.append("Meals")

    if not re.search(r"\bnot\s+in(?:cl|lc)uded\b|\bexcluded\b|\bwithout\s+meals?\b|\bto\s+be\s+bought\s+on\s+(?:site|spot)\b|\btickets?\s+to\s+be\s+purchased\s+(?:locally|on\s+site)\b|\bticket\s+counter\b", source, flags=re.IGNORECASE):
        return []

    sections: list[str] = []
    for match in re.finditer(r"(?:^|\n)\s*not\s+in(?:cl|lc)uded\b\s*[:?]?", source, flags=re.IGNORECASE):
        after = source[match.end():]
        stop = re.search(
            r"(?:\n\s*)?(?:What\s+to\s+expect\??|What'?s\s+included\??|What’s\s+included\??|Overview|Highlights|Itinerary|Please\s+note|Important\s+info|Pick[-\s]*up\s*/\s*meeting\s*point)\b",
            after,
            flags=re.IGNORECASE,
        )
        if stop:
            after = after[:stop.start()]
        sections.append(after)

    # Compact rows may say "Food and drinks are excluded" without a formal section.
    for match in re.finditer(r"\b([^\n.;|]*?\b(?:are\s+)?excluded)\b", source, flags=re.IGNORECASE):
        sections.append(match.group(1))

    items: list[str] = list(direct_items)
    for section in sections:
        for item in _split_exclusion_phrases(section):
            if item and item not in items:
                items.append(item)
    return items


def _specific_cost_not_included_label(row) -> str:
    items = _row_specific_not_included_items(row)
    if not items:
        return ""
    title = sanitize_client_text(commercial_row_title(row))
    if not title:
        return ""
    phrase_items = []
    for index, item in enumerate(items):
        text = sanitize_client_text(str(item or "").strip())
        if index > 0 and text:
            text = text[:1].lower() + text[1:]
        phrase_items.append(text)
    if len(phrase_items) == 1:
        detail = phrase_items[0]
    else:
        detail = ", ".join(phrase_items[:-1]) + f" and {phrase_items[-1]}"
    return sanitize_client_text(f"{title}: {detail}")

def _commercial_status(row):
    return str(row.get("commercial_status") or "").strip().lower()


def _commercial_reason(row):
    return str(row.get("commercial_reason") or "").strip().lower()


def _row_search_text(row):
    return _transport_row_search_text(row)


def _is_self_transfer_row(row):
    return _transport_is_self_transfer_row(row)


def _is_flight_row(row):
    return _transport_is_flight_row(row)


def _is_transport_row(row):
    return _transport_is_transport_row(row)


def _is_cost_not_included_row(row):
    text = _row_search_text(row)
    return (
        _commercial_reason(row) == "cost_not_included"
        or "cost not included" in text
        or "price not included" in text
        or "not included" in text
        or "without meal" in text
        or "to be bought on site" in text
        or "to be bought on spot" in text
        or "ticket counter" in text
        or "on spot" in text
        or "on site" in text
    )


def _rental_cost_not_included_label(row):
    """Return a precise rental cost exclusion without excluding the rental row.

    Supplier rows commonly describe the included rental package and then add a
    small commercial caveat such as ``Not included: Safety deposit``. The final
    exclusions should surface the caveat, not the whole rental pick-up title.
    """

    text = _row_search_text(row)
    if "rental" not in text or "not included" not in text:
        return ""
    if "deposit" in text:
        return "Rental vehicle safety deposit"
    if "fuel" in text:
        return "Rental vehicle fuel costs"
    if "parking" in text:
        return "Rental vehicle parking costs"
    return "Rental vehicle costs marked as not included"


def row_date_suffix(row):
    text = format_client_date(row.get("start_date"))
    return f" - {text}" if text else ""


def self_arranged_flight_notice(row) -> str:
    """Return a clear commercial exclusion label for a self-arranged flight."""

    return _transport_self_arranged_flight_notice(row)


def commercial_row_title(row):
    row_type = get_row_type(row)
    title = ""
    if _is_self_transfer_row(row):
        return _transport_self_transfer_exclusion_title(row)
    if row_type == "Activity":
        title = create_client_activity_title(row)
    if not title:
        title = _transport_commercial_title(row)
    title = title or row.get("title") or row.get("original_title") or row.get("details")
    title = sanitize_client_text(polish_title(str(title or "").strip()))
    return title[:120].strip(" -:|")


def specific_self_arranged_items(parsed_rows):
    items = []
    for row in main_rows_only(parsed_rows or []):
        text = f'{row.get("title", "")} {row.get("details", "")}'.lower()
        if not (is_self_arranged(row) or row.get("commercial_status") == "self_arranged" or "self transfer" in text):
            continue
        title = sanitize_client_text(commercial_row_title(row))
        if not title:
            continue
        label = sanitize_client_text(f"{title}{row_date_suffix(row)}")
        add_unique(items, label)
    return items


def specific_optional_items(parsed_rows):
    items = []
    for row in optional_rows_only(parsed_rows or []):
        title = sanitize_client_text(commercial_row_title(row))
        if not title:
            continue
        add_unique(items, f"{title}{row_date_suffix(row)}")
    return items


def create_specific_exclusion_sections(parsed_rows):
    """Return itinerary-specific exclusions grouped under client-facing headings.

    The grouping is intentionally driven by row commercial metadata first and
    conservative text markers second. That keeps optional/self-arranged logic
    from becoming a broad text search that can accidentally affect later rows.
    """

    sections = {key: [] for key, _ in EXCLUSION_SECTION_ORDER}

    for row in parsed_rows or []:
        title = sanitize_client_text(commercial_row_title(row))
        if not title:
            continue

        label = sanitize_client_text(f"{title}{row_date_suffix(row)}")
        row_type = str(row.get("group_tour_semantic_type") or get_row_type(row))
        status = _commercial_status(row)

        rental_exclusion = _rental_cost_not_included_label(row)
        if rental_exclusion:
            add_unique(sections["costs_not_included"], rental_exclusion)
            # The included rental row can continue through normal inclusion
            # handling, but it should not add a raw pick-up title to exclusions.
            continue

        if is_optional_row(row):
            if row_type == "Activity":
                add_unique(sections["optional_experiences"], label)
            elif row_type == "Hotel":
                add_unique(sections["optional_hotels"], label)
            elif _is_transport_row(row):
                add_unique(sections["optional_transfers"], label)
            else:
                add_unique(sections["optional_hotels"], label)
            continue

        if status == "self_arranged" or is_self_arranged(row) or _is_self_transfer_row(row):
            if _is_self_transfer_row(row):
                add_unique(sections["self_transfers"], label)
                notes = split_self_transfer_notes(_row_search_text(row))
                if any("private transfer may" in note.lower() for note in notes):
                    add_unique(sections["costs_not_included"], "Private transfer supplement, if requested locally")
            elif _is_flight_row(row):
                add_unique(sections["self_arranged_flights"], label)
            else:
                add_unique(sections["costs_not_included"], label)
            continue

        if status == "excluded" or _is_cost_not_included_row(row):
            specific_label = _specific_cost_not_included_label(row)
            add_unique(sections["costs_not_included"], specific_label or label)

    return {key: value for key, value in sections.items() if value}



def _add_unique_structured(items, label, row=None, row_index=0):
    item = _structured_item(label, row=row, row_index=row_index)
    if not item:
        return
    key = (item["label"].lower(), tuple(item.get("source_row_ids") or ()))
    existing = {
        (str(current.get("label", "")).lower(), tuple(current.get("source_row_ids") or ()))
        for current in items
        if isinstance(current, dict)
    }
    if key not in existing:
        items.append(item)


def create_source_aware_exclusion_sections(parsed_rows):
    """Return itinerary-specific exclusions with source-row identity preserved.

    ``create_specific_exclusion_sections`` stays as the legacy string API. This
    source-aware companion is used by the structured model so self-arranged,
    optional and activity-specific exclusion rows can be audited back to the row
    that produced them. That prevents the renderer/editor from flattening the
    page into anonymous paragraphs and makes missing exclusion coverage visible.
    """

    sections = {key: [] for key, _ in EXCLUSION_SECTION_ORDER}

    for row_index, row in enumerate(parsed_rows or []):
        title = sanitize_client_text(commercial_row_title(row))
        if not title:
            continue

        label = sanitize_client_text(f"{title}{row_date_suffix(row)}")
        row_type = str(row.get("group_tour_semantic_type") or get_row_type(row))
        status = _commercial_status(row)

        rental_exclusion = _rental_cost_not_included_label(row)
        if rental_exclusion:
            _add_unique_structured(sections["costs_not_included"], rental_exclusion, row, row_index)
            continue

        if is_optional_row(row):
            if row_type == "Activity":
                _add_unique_structured(sections["optional_experiences"], label, row, row_index)
            elif row_type == "Hotel":
                _add_unique_structured(sections["optional_hotels"], label, row, row_index)
            elif _is_transport_row(row):
                _add_unique_structured(sections["optional_transfers"], label, row, row_index)
            else:
                _add_unique_structured(sections["optional_hotels"], label, row, row_index)
            continue

        if status == "self_arranged" or is_self_arranged(row) or _is_self_transfer_row(row):
            if _is_self_transfer_row(row):
                _add_unique_structured(sections["self_transfers"], label, row, row_index)
                notes = split_self_transfer_notes(_row_search_text(row))
                if any("private transfer may" in note.lower() for note in notes):
                    _add_unique_structured(sections["costs_not_included"], "Private transfer supplement, if requested locally", row, row_index)
            elif _is_flight_row(row):
                _add_unique_structured(sections["self_arranged_flights"], label, row, row_index)
            else:
                _add_unique_structured(sections["costs_not_included"], label, row, row_index)
            continue

        if status == "excluded" or _is_cost_not_included_row(row):
            specific_label = _specific_cost_not_included_label(row)
            _add_unique_structured(sections["costs_not_included"], specific_label or label, row, row_index)

    return {key: value for key, value in sections.items() if value}


def flatten_specific_exclusion_sections(sections, limit_per_section=8):
    """Flatten structured exclusion sections for the existing final-page renderer."""

    items = []
    for key, heading in EXCLUSION_SECTION_ORDER:
        section_items = list((sections or {}).get(key) or [])
        if not section_items:
            continue
        add_unique(items, heading)
        for item in section_items[:limit_per_section]:
            add_unique(items, item)
        if len(section_items) > limit_per_section:
            add_unique(items, f"and {len(section_items) - limit_per_section} more")
    return items



def _commercial_rule_item(label, source_sections):
    source_ids = []
    for items in (source_sections or {}).values():
        for item in items or []:
            if not isinstance(item, dict):
                continue
            for row_id in item.get("source_row_ids") or []:
                if row_id and row_id not in source_ids:
                    source_ids.append(row_id)
    return {"label": label, "source_row_ids": source_ids[:20]}


def _default_exclusion_items():
    return [{"label": item, "source_row_ids": []} for item in DEFAULT_WHATS_NOT_INCLUDED_ITEMS]


def create_structured_whats_not_included(parsed_rows=None):
    """Return exclusions as source-aware structured sections.

    The legacy ``create_whats_not_included`` API still returns strings. This
    structured API returns section dictionaries whose items keep labels separate
    from detail/source metadata.  That lets preview, editor and PDF render a
    stable list while validation can prove self-arranged/optional/excluded rows
    still have a visible exclusion entry.
    """

    rows = parsed_rows or []
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()
    specific_sections = create_source_aware_exclusion_sections(rows)

    sections = []
    for key, heading in EXCLUSION_SECTION_ORDER:
        items = list(specific_sections.get(key) or [])
        if items:
            sections.append({"section_id": key, "title": heading, "items": items})

    commercial_rules = []
    if any(specific_sections.get(key) for key in ["self_arranged_flights", "self_transfers", "costs_not_included"]):
        commercial_rules.append(_commercial_rule_item(
            "Self-arranged flights or transport unless specifically stated as included",
            {key: specific_sections.get(key) or [] for key in ["self_arranged_flights", "self_transfers", "costs_not_included"]},
        ))
        for row_index, row in enumerate(rows):
            if (_commercial_status(row) == "self_arranged" or is_self_arranged(row)) and _is_flight_row(row):
                notice = _structured_item(self_arranged_flight_notice(row), row=row, row_index=row_index)
                if notice and notice["label"] not in {item.get("label") for item in commercial_rules if isinstance(item, dict)}:
                    commercial_rules.append(notice)
    if any(specific_sections.get(key) for key in ["optional_experiences", "optional_transfers", "optional_hotels"]):
        commercial_rules.append(_commercial_rule_item(
            "Optional add-ons and experiences unless specifically selected",
            {key: specific_sections.get(key) or [] for key in ["optional_experiences", "optional_transfers", "optional_hotels"]},
        ))
    if "optional addon" in text or "optional add-on" in text or "optional add on" in text:
        item = _commercial_rule_item("Optional add-ons and experiences unless specifically selected", specific_sections)
        if item["label"] not in {existing["label"] for existing in commercial_rules}:
            commercial_rules.append(item)
    if "excludes" in text or "not included" in text or "to be bought on site" in text or "to be bought on spot" in text or "ticket counter" in text:
        item = _commercial_rule_item("Tickets or services marked as excluded or to be bought on site", specific_sections)
        if item["label"] not in {existing["label"] for existing in commercial_rules}:
            commercial_rules.append(item)
    if commercial_rules:
        sections.append({"section_id": "commercial_rules", "title": "Commercial notes", "items": commercial_rules})

    sections.append({"section_id": "general", "title": "General exclusions", "items": _default_exclusion_items()})
    return sections


def create_whats_not_included(parsed_rows=None):
    rows = parsed_rows or []
    items = list(DEFAULT_WHATS_NOT_INCLUDED_ITEMS)
    text = " ".join(f'{row.get("title", "")} {row.get("details", "")}' for row in rows).lower()

    sections = create_specific_exclusion_sections(rows)
    structured_items = flatten_specific_exclusion_sections(sections)
    itinerary_specific_items = list(structured_items)

    if any(sections.get(key) for key in ["self_arranged_flights", "self_transfers", "costs_not_included"]):
        add_unique(itinerary_specific_items, "Self-arranged flights or transport unless specifically stated as included")

    if any(sections.get(key) for key in ["optional_experiences", "optional_transfers", "optional_hotels"]):
        add_unique(itinerary_specific_items, "Optional add-ons and experiences unless specifically selected")

    if "optional addon" in text or "optional add-on" in text or "optional add on" in text:
        add_unique(itinerary_specific_items, "Optional add-ons and experiences unless specifically selected")
    if "excludes" in text or "not included" in text or "to be bought on site" in text or "to be bought on spot" in text or "ticket counter" in text:
        add_unique(itinerary_specific_items, "Tickets or services marked as excluded or to be bought on site")

    if itinerary_specific_items:
        items = items[:1] + itinerary_specific_items + items[1:]
    return items
