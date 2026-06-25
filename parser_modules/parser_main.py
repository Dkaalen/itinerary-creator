"""Top-level itinerary parser orchestration."""

import re

import diagnostics

from parser_modules.commercial_status import infer_optional_row_type
from parser_modules.common import (
    KNOWN_TYPES,
    clean_space,
    looks_like_date,
    looks_like_non_itinerary_type,
    normalize_type,
)
from parser_modules.contextual_city import apply_context_city, context_city_from_row
from parser_modules.date_fields import (
    _date_derived_hotel_nights,
    _excel_serial_date,
    _parse_itinerary_date,
    excel_serial_date,
)
from parser_modules.city_inference import _infer_city_from_text
from parser_modules.raw_row_context import (
    _fixed_format_city_only_description,
    _fix_common_text_for_row,
    fixed_format_city_only_description,
)
from parser_modules.row_builder import build_base_row
from parser_modules.row_enrichment import enrich_parsed_row
from parser_modules.rows import (
    find_city_cell,
    find_day_index,
    find_description_cell,
    get_description_index,
    make_row_id,
    preprocess_raw_rows,
)


def _extract_date_context(parts, *, type_index, description_index, item_type):
    night_count_hint = ""
    date_values = []

    for part in parts[type_index + 1:description_index]:
        value = clean_space(part)

        if not value:
            continue

        if looks_like_date(value) or excel_serial_date(value):
            date_values.append(value)
            continue

        if not night_count_hint and item_type == "Hotel" and re.fullmatch(r"\d+(?:\.0)?", value):
            nights_value = int(float(value))
            if 0 < nights_value <= 30:
                night_count_hint = str(nights_value)
                continue

    start_date = date_values[0] if len(date_values) >= 1 else ""
    end_date = date_values[1] if len(date_values) >= 2 else ""
    return start_date, end_date, night_count_hint


def _normalize_row_type(item_type, description):
    is_optional = False

    if item_type.lower() == "optional":
        is_optional = True
        item_type = infer_optional_row_type(description)

    if item_type.lower() in {
        "activity upgrade",
        "transfer package",
        "single supplement fee",
        "extra hotel night",
    }:
        is_optional = True

    return item_type, is_optional


def _warn_or_skip_unknown_type(item_type, raw_line):
    if item_type.lower() in KNOWN_TYPES:
        return False
    if looks_like_non_itinerary_type(item_type):
        diagnostics.warn(
            "skipped_non_itinerary_row",
            f"Skipped non-itinerary calculator row type '{item_type}'",
            raw_value=raw_line,
        )
        return True
    diagnostics.warn(
        "unknown_type",
        f"Unrecognised row type '{item_type}' — treated as-is",
        raw_value=raw_line,
    )
    return False


def parse_itinerary(raw_text):
    rows = []
    seen_row_ids = set()
    current_day = ""
    last_context_city = ""
    day_context_city = {}
    pending_city_rows_by_day = {}

    for line_number, raw_line in enumerate(preprocess_raw_rows(raw_text), start=1):
        if not raw_line.strip():
            continue

        parts = raw_line.rstrip("\n").split("\t")
        row_marker_optional = False
        if parts and parts[0] in {"__OPTIONAL__", "__MAIN__"}:
            row_marker_optional = parts[0] == "__OPTIONAL__"
            parts = parts[1:]

        if not any(part.strip() for part in parts):
            continue

        day_index = find_day_index(parts)

        if day_index is not None:
            current_day = clean_space(parts[day_index])
        elif not current_day:
            diagnostics.warn(
                "skipped_row",
                "Skipped row because no day could be detected",
                raw_value=raw_line,
            )
            continue

        type_index = day_index + 1 if day_index is not None else 1
        item_type = normalize_type(parts[type_index]) if len(parts) > type_index else ""
        original_item_type = item_type

        if not item_type:
            diagnostics.warn(
                "missing_type",
                f"Skipped {current_day} row because no row type could be detected",
                raw_value=raw_line,
            )
            continue

        description_index = get_description_index(parts)
        description = find_description_cell(parts)
        if len(parts) > 10 and not clean_space(parts[10]) and description_index < 9:
            description = ""
            description_index = 10
        item_type, type_optional = _normalize_row_type(item_type, description)
        is_optional = row_marker_optional or type_optional

        if _warn_or_skip_unknown_type(item_type, raw_line):
            continue

        if not description:
            diagnostics.warn(
                "missing_description",
                f"Skipped {current_day} {item_type} row because no description could be detected",
                raw_value=raw_line,
            )
            continue

        start_date, end_date, night_count_hint = _extract_date_context(
            parts,
            type_index=type_index,
            description_index=description_index,
            item_type=item_type,
        )

        separate_city = find_city_cell(parts, description_index)
        city_only_cell, city_only_description = fixed_format_city_only_description(parts, description_index, item_type)
        if city_only_cell and city_only_description:
            separate_city = city_only_cell
            description = city_only_description

        row_id = make_row_id(current_day, item_type, start_date, end_date, description)
        if is_optional:
            row_id = f"opt_{row_id}"
            diagnostics.warn(
                "optional_addon",
                f"Detected optional add-on row for {current_day}",
                raw_value=description,
            )

        if row_id in seen_row_ids:
            diagnostics.warn(
                "duplicate_row",
                f"Skipped duplicate row on {current_day}",
                raw_value=description,
            )
            continue

        seen_row_ids.add(row_id)

        row = build_base_row(
            raw_line=raw_line,
            line_number=line_number,
            row_id=row_id,
            is_optional=is_optional,
            current_day=current_day,
            item_type=item_type,
            original_item_type=original_item_type,
            start_date=start_date,
            end_date=end_date,
            description=description,
        )
        row = enrich_parsed_row(
            row,
            description=description,
            item_type=item_type,
            separate_city=separate_city,
            start_date=start_date,
            end_date=end_date,
            night_count_hint=night_count_hint,
            current_day=current_day,
        )

        context_city = day_context_city.get(current_day) or last_context_city
        apply_context_city(row, context_city)

        row_context_city = context_city_from_row(row)
        if row_context_city:
            day_context_city[current_day] = row_context_city
            last_context_city = row_context_city
            for pending_row in pending_city_rows_by_day.pop(current_day, []):
                apply_context_city(pending_row, row_context_city)
        elif normalize_type(item_type) in {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry", "Leisure"}:
            pending_city_rows_by_day.setdefault(current_day, []).append(row)

        rows.append(row)

    return rows
