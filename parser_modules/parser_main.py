import diagnostics
from datetime import datetime, timedelta
from place_aliases import canonicalize_place_name, is_known_place

from parser_modules.common import *  # noqa: F401,F403
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
from parser_modules.commercial_status import (
    infer_commercial_status,
    infer_optional_row_type,
    initial_commercial_state,
    mark_optional_row,
    REASON_OPTIONAL_TEXT_PREFIX,
)
from parser_modules.row_quality import annotate_parser_quality
from parser_modules.rows import (
    find_city_cell,
    find_day_index,
    find_description_cell,
    get_description_index,
    make_row_id,
    preprocess_raw_rows,
)



def _parse_itinerary_date(value):
    text = clean_space(value)
    if not text:
        return None
    serial = _excel_serial_date(text)
    if serial:
        try:
            return datetime(1899, 12, 30) + timedelta(days=int(float(text)))
        except Exception:
            return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _date_derived_hotel_nights(start_date, end_date):
    start = _parse_itinerary_date(start_date)
    end = _parse_itinerary_date(end_date)
    if not start or not end:
        return ""
    nights = (end.date() - start.date()).days
    if 0 < nights <= 60:
        return str(nights)
    return ""

def _fix_common_text_for_row(value, item_type):
    """Apply broad cleanup without rewriting supplier-owned hotel names."""

    if normalize_type(item_type) != "Hotel":
        return fix_common_text(value)

    protected = re.sub(r"\bAurora\b", "__HOTEL_AURORA__", str(value or ""), flags=re.IGNORECASE)
    cleaned = fix_common_text(protected)
    return cleaned.replace("__HOTEL_AURORA__", "Aurora")


def _excel_serial_date(value):
    """Return True for Excel serial dates commonly pasted from calculator rows."""

    text = clean_space(value)
    return bool(re.fullmatch(r"4\d{4}(?:\.0)?", text))


def _fixed_format_city_only_description(parts, description_index, item_type):
    """Detect the app's fixed Excel paste shape when Details is blank.

    The canonical row has City at index 9 and Details at index 10. If Details is
    empty, the old rightmost-cell heuristic used City as the description and
    then lost the city. Preserve the city and create a safe fallback title so
    the row does not break generation.
    """

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


def _infer_city_from_text(text):
    """Infer obvious Nordic city mentions from otherwise city-less titles."""

    source = clean_space(text)
    if not source:
        return ""
    patterns = [
        r"\bin\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\s*[,|:-]|\s*$)",
        r"\b(?:from|to)\s+([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})(?:\s*[,|:-]|\s*$)",
        r"^([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{2,35})\s+(?:Hop|Walking|City|Sightseeing|Private|Shuttle|Airport|Leisure)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if not match:
            continue
        candidate = clean_space(match.group(1)).strip(" .,-|:")
        # Trim common trailing service nouns that can be captured after "in".
        candidate = re.split(r"\s+(?:Guide|Ticket|Tour|Walk|Bus|Boat|Cruise|Safari|Transfer)\b", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .,-|:")
        if candidate and is_valid_city_value(candidate) and is_known_place(candidate):
            return canonicalize_place_name(candidate)
    return ""


def parse_itinerary(raw_text):
    rows = []
    seen_row_ids = set()
    current_day = ""

    for line_number, raw_line in enumerate(preprocess_raw_rows(raw_text), start=1):
        if not raw_line.strip():
            continue

        parts = raw_line.rstrip("\n").split("\t")
        is_optional = False
        if parts and parts[0] in {"__OPTIONAL__", "__MAIN__"}:
            is_optional = parts[0] == "__OPTIONAL__"
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

        if item_type.lower() == "optional":
            is_optional = True
            item_type = infer_optional_row_type(description)

        # Iceland package worksheets keep commercial add-ons as explicit row
        # types. They are related to the package but are not automatically
        # included itinerary experiences.
        if item_type.lower() in {
            "activity upgrade",
            "transfer package",
            "single supplement fee",
            "extra hotel night",
        }:
            is_optional = True

        if item_type.lower() not in KNOWN_TYPES:
            if looks_like_non_itinerary_type(item_type):
                diagnostics.warn(
                    "skipped_non_itinerary_row",
                    f"Skipped non-itinerary calculator row type '{item_type}'",
                    raw_value=raw_line,
                )
                continue
            diagnostics.warn(
                "unknown_type",
                f"Unrecognised row type '{item_type}' — treated as-is",
                raw_value=raw_line,
            )

        if not description:
            diagnostics.warn(
                "missing_description",
                f"Skipped {current_day} {item_type} row because no description could be detected",
                raw_value=raw_line,
            )
            continue

        night_count_hint = ""
        date_values = []

        for part in parts[type_index + 1:description_index]:
            value = clean_space(part)

            if not value:
                continue

            if not night_count_hint and item_type == "Hotel" and value.isdigit():
                night_count_hint = value
                continue

            if looks_like_date(value) or _excel_serial_date(value):
                date_values.append(value)

        start_date = date_values[0] if len(date_values) >= 1 else ""
        end_date = date_values[1] if len(date_values) >= 2 else ""

        separate_city = find_city_cell(parts, description_index)
        city_only_cell, city_only_description = _fixed_format_city_only_description(parts, description_index, item_type)
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

        commercial_status, commercial_reason = initial_commercial_state(is_optional)

        row = {
            "raw": clean_space(raw_line),
            "line_number": line_number,
            "row_id": row_id,
            "is_optional": is_optional,
            "day": current_day,
            "type": item_type,
            "source_type": original_item_type,
            "effective_type": "",
            "commercial_status": commercial_status,
            "commercial_reason": commercial_reason,
            "start_date": start_date,
            "end_date": end_date,
            "city": "",
            "title": "",
            "details": description,
            "time": "",
            "duration": "",
            "meeting_point": "",
            "end_point": "",
            "notable_sights": [],
            "includes": [],
            "luggage_included": "",
            "hotel_name": "",
            "hotel_nights": "",
            "room_category": "",
            "meal_plan": "",
            "star_rating": "",
        }

        main_text = description.strip().strip('"')

        # Some exported rows duplicate the row type inside the description,
        # for example ``Activity: Copenhagen: Spend time at leisure``.  Strip
        # that administrative prefix before city/title extraction so the real
        # city can still be detected.
        type_prefix = re.match(r"^\s*(Activity|Transfer|Hotel|Train|Flight|Cruise|Ferry|Transport|Leisure|Arrival|Departure)\s*:\s*(.+)$", main_text, flags=re.IGNORECASE)
        if type_prefix and type_prefix.group(1).lower() == normalize_type(item_type).lower():
            main_text = type_prefix.group(2).strip()

        # Pipe-format activity rows often arrive as ``City | Product | Time |
        # Includes ...``.  Pull the first part into the city before generic
        # title cleanup trims the supplier-style pipe sections.
        if not separate_city and "|" in main_text:
            first_pipe_part, rest_pipe_text = main_text.split("|", 1)
            if is_valid_city_value(first_pipe_part) and not re.search(r"\bnorway\s+in\s+a\s+nutshell\b", first_pipe_part, flags=re.IGNORECASE):
                row["city"] = clean_space(first_pipe_part)
                main_text = rest_pipe_text.strip()

        # Optional add-ons often arrive as normal activity rows where the first
        # phrase says "Optional Addon (...)" rather than as a separate optional
        # section. Mark them here so they stay out of the included day plan and
        # commercial inclusions while still being available for optional pages.
        if not is_optional and is_explicit_optional_text(main_text):
            is_optional = True
            mark_optional_row(row, REASON_OPTIONAL_TEXT_PREFIX)

        if separate_city:
            row["city"] = separate_city

            if ":" in main_text:
                possible_city, rest = main_text.split(":", 1)
                if clean_space(possible_city).lower() == clean_space(separate_city).lower():
                    main_text = rest.strip()

        elif ":" in main_text:
            possible_city, rest = main_text.split(":", 1)
            # Do not treat the text before a clock-time colon as a city.
            # Example: ``Bergen | Private Fjord Cruise | 10:00 - 14:00``.
            city_prefix_is_safe = "|" not in possible_city and not re.search(r"\d\s*$", possible_city)
            if city_prefix_is_safe and is_valid_city_value(possible_city):
                row["city"] = clean_space(possible_city)
                main_text = rest.strip()

        main_text = _fix_common_text_for_row(main_text, item_type)
        check_for_unknown_typos(main_text, context=current_day)
        row["details"] = _fix_common_text_for_row(description, item_type)
        check_for_unknown_typos(row["details"], context=current_day)
        row["city"] = canonicalize_place_name(fix_common_text(row.get("city", "")))
        if not row["city"]:
            row["city"] = _infer_city_from_text(" ".join(part for part in [main_text, description] if part))

        important_types_for_city = {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry"}
        if not is_optional and normalize_type(item_type) in important_types_for_city and not row["city"]:
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
            date_derived_nights = _date_derived_hotel_nights(start_date, end_date)
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
            route_origin, route_destination = extract_route_points(" ".join(part for part in [row.get("title", ""), row.get("details", "")] if part))
            if route_origin:
                row["route_origin"] = route_origin
            if route_destination:
                row["route_destination"] = route_destination

        row = standardize_row_text(row)
        row = annotate_parser_quality(row)

        status, reason = infer_commercial_status(row.get("is_optional"), item_type, row.get("title", ""), row.get("details", ""))
        row["commercial_status"] = status
        row["commercial_reason"] = row.get("commercial_reason") if status == "optional" else reason

        rows.append(row)

    return rows
