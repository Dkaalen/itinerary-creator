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
from parser_modules.date_fields import (
    _date_derived_hotel_nights,
    _excel_serial_date,
    _parse_itinerary_date,
    excel_serial_date,
)
from parser_modules.city_inference import _infer_city_from_text
from parser_modules.raw_row_context import extract_city_and_description
from parser_modules.row_builder import build_base_row
from parser_modules.row_enrichment import enrich_parsed_row
from parser_modules.wrapper_row_types import resolve_source_wrapper_type
from parser_modules.parser_line import day_from_parts, has_content, line_parts
from parser_modules.parser_state import ParserState
from parser_modules.rows import (
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
    state = ParserState()

    for line_number, raw_line in enumerate(preprocess_raw_rows(raw_text), start=1):
        if not raw_line.strip():
            continue

        parts, row_marker_optional = line_parts(raw_line)
        if not has_content(parts):
            continue

        day_index, detected_day = day_from_parts(parts)
        if detected_day:
            state.update_day(detected_day)
        elif not state.current_day:
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
                f"Skipped {state.current_day} row because no row type could be detected",
                raw_value=raw_line,
            )
            continue

        parsed_row = _parse_line_row(
            raw_line=raw_line,
            line_number=line_number,
            parts=parts,
            type_index=type_index,
            item_type=item_type,
            original_item_type=original_item_type,
            row_marker_optional=row_marker_optional,
            current_day=state.current_day,
        )
        if parsed_row is None:
            continue

        row_id, row = parsed_row
        if state.has_seen(row_id):
            diagnostics.warn(
                "duplicate_row",
                f"Skipped duplicate row on {state.current_day}",
                raw_value=row.get("details", ""),
            )
            continue

        state.remember_row_id(row_id)
        state.apply_context(row)
        state.register_row_context(row, row.get("type", ""))
        rows.append(row)

    return rows


def _parse_line_row(
    *,
    raw_line: str,
    line_number: int,
    parts: list[str],
    type_index: int,
    item_type: str,
    original_item_type: str,
    row_marker_optional: bool,
    current_day: str,
) -> tuple[str, dict] | None:
    description_index = get_description_index(parts)
    description = find_description_cell(parts)
    if len(parts) > 10 and not clean_space(parts[10]) and description_index < 9:
        description = ""
        description_index = 10

    item_type = resolve_source_wrapper_type(item_type, description)
    item_type, type_optional = _normalize_row_type(item_type, description)
    is_optional = row_marker_optional or type_optional

    if _warn_or_skip_unknown_type(item_type, raw_line):
        return None
    if not description:
        diagnostics.warn(
            "missing_description",
            f"Skipped {current_day} {item_type} row because no description could be detected",
            raw_value=raw_line,
        )
        return None

    start_date, end_date, night_count_hint = _extract_date_context(
        parts,
        type_index=type_index,
        description_index=description_index,
        item_type=item_type,
    )
    separate_city, description = extract_city_and_description(parts, description_index, item_type, description)

    row_id = make_row_id(current_day, item_type, start_date, end_date, description)
    if is_optional:
        row_id = f"opt_{row_id}"
        diagnostics.warn(
            "optional_addon",
            f"Detected optional add-on row for {current_day}",
            raw_value=description,
        )

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
    return row_id, row
