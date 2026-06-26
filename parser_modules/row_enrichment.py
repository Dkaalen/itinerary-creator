"""Post-context enrichment for parser itinerary rows."""

import re

import diagnostics
from place_aliases import canonicalize_place_name
from shared.commercial_markers import has_self_arranged_marker
from parser_modules.city_inference import infer_city_from_text
from parser_modules.commercial_status import (
    REASON_OPTIONAL_TEXT_PREFIX,
    infer_commercial_status,
    mark_optional_row,
)
from parser_modules.type_detection import is_explicit_optional_text
from parser_modules.common import (
    check_for_unknown_typos,
    clean_space,
    extract_route_points,
    fix_common_text,
    is_valid_city_value,
    normalize_type,
)
from parser_modules.date_fields import date_derived_hotel_nights
from parser_modules.details import (
    clean_title,
    detect_effective_type,
    extract_detail,
    split_comma_list,
    standardize_row_text,
)
from parser_modules.extractors import (
    extract_duration_from_description,
    extract_includes_from_description,
    extract_luggage_included,
    extract_meeting_point_from_description,
    extract_time_from_description,
)
from parser_modules.hotels import parse_hotel_details
from parser_modules.raw_row_context import fix_common_text_for_row, strip_matching_type_prefix
from parser_modules.row_quality import annotate_parser_quality


def enrich_parsed_row(
    row,
    *,
    description,
    item_type,
    separate_city,
    start_date,
    end_date,
    night_count_hint,
    current_day,
):
    """Fill derived fields for a parsed itinerary row without changing behavior."""

    main_text = description.strip().strip('"')
    main_text = strip_matching_type_prefix(main_text, item_type)

    if not separate_city and "|" in main_text:
        first_pipe_part, rest_pipe_text = main_text.split("|", 1)
        if is_valid_city_value(first_pipe_part) and not re.search(r"\bnorway\s+in\s+a\s+nutshell\b", first_pipe_part, flags=re.IGNORECASE):
            row["city"] = clean_space(first_pipe_part)
            main_text = rest_pipe_text.strip()

    if not row.get("is_optional") and is_explicit_optional_text(main_text):
        mark_optional_row(row, REASON_OPTIONAL_TEXT_PREFIX)

    if separate_city:
        row["city"] = separate_city

        if ":" in main_text:
            possible_city, rest = main_text.split(":", 1)
            if clean_space(possible_city).lower() == clean_space(separate_city).lower():
                main_text = rest.strip()

    elif ":" in main_text:
        possible_city, rest = main_text.split(":", 1)
        city_prefix_is_safe = "|" not in possible_city and not re.search(r"\d\s*$", possible_city)
        if city_prefix_is_safe and is_valid_city_value(possible_city):
            row["city"] = clean_space(possible_city)
            main_text = rest.strip()

    main_text = fix_common_text_for_row(main_text, item_type)
    check_for_unknown_typos(main_text, context=current_day)
    row["details"] = fix_common_text_for_row(description, item_type)
    check_for_unknown_typos(row["details"], context=current_day)
    row["city"] = canonicalize_place_name(fix_common_text(row.get("city", "")))
    if not row["city"]:
        row["city"] = infer_city_from_text(" ".join(part for part in [main_text, description] if part))

    important_types_for_city = {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry"}
    if not row.get("is_optional") and normalize_type(item_type) in important_types_for_city and not row["city"]:
        diagnostics.warn(
            "missing_city",
            f"Could not extract a city from {current_day} {item_type}: {description[:80]}",
            raw_value=description,
        )

    row["title"] = clean_title(main_text)
    row["original_title"] = row["title"]
    row["time"] = extract_time_from_description(main_text)
    row["duration"] = extract_duration_from_description(main_text)
    row["meeting_point"] = extract_meeting_point_from_description(main_text)
    row["end_point"] = extract_detail(main_text, "End point")
    notable_source = (
        extract_detail(main_text, "Notable Sights")
        or extract_detail(main_text, "Highlights")
        or extract_detail(main_text, "Stops")
    )
    row["notable_sights"] = split_comma_list(notable_source)
    row["includes"] = extract_includes_from_description(main_text)
    row["luggage_included"] = extract_luggage_included(main_text)

    if normalize_type(item_type) == "Hotel":
        hotel_details = parse_hotel_details(row, main_text, night_count_hint=night_count_hint)
        date_derived_nights = date_derived_hotel_nights(start_date, end_date)
        if date_derived_nights:
            parsed_nights = clean_space(hotel_details.get("hotel_nights", ""))
            if parsed_nights and parsed_nights != date_derived_nights:
                hotel_details["source_hotel_nights"] = parsed_nights
                hotel_details["hotel_night_mismatch"] = f"source={parsed_nights}; dates={date_derived_nights}"
                diagnostics.warn(
                    "hotel_night_date_mismatch",
                    f"Hotel stay dates imply {date_derived_nights} nights but the text says {parsed_nights} nights",
                    raw_value=main_text,
                )
            if parsed_nights and has_self_arranged_marker(main_text, hotel_details.get("hotel_name", "")):
                hotel_details["hotel_nights"] = parsed_nights
            else:
                hotel_details["hotel_nights"] = date_derived_nights
        row.update(hotel_details)
        if row.get("hotel_name"):
            row["title"] = row["hotel_name"]

    row["effective_type"] = detect_effective_type(
        row["type"],
        row["title"],
        row["details"],
    )

    if row["effective_type"] in {"Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry"}:
        route_source = row.get("details", "") or " ".join(part for part in [row.get("title", ""), row.get("details", "")] if part)
        route_origin, route_destination = extract_route_points(route_source)
        if route_destination and not route_origin and row.get("city"):
            route_origin = row.get("city", "")
        if route_origin:
            row["route_origin"] = route_origin
        if route_destination:
            row["route_destination"] = route_destination

    row = standardize_row_text(row)
    row = annotate_parser_quality(row)

    status, reason = infer_commercial_status(row.get("is_optional"), item_type, row.get("title", ""), row.get("details", ""))
    row["commercial_status"] = status
    row["commercial_reason"] = row.get("commercial_reason") if status == "optional" else reason
    return row
