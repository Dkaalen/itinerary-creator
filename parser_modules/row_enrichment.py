"""Post-context enrichment for parser itinerary rows."""

from parser_modules.commercial_status import REASON_OPTIONAL_TEXT_PREFIX, mark_optional_row
from parser_modules.row_enrichment_steps import (
    apply_city_and_quality,
    apply_common_detail_fields,
    apply_effective_type_and_routes,
    apply_hotel_fields,
    finalize_row_quality_and_status,
    prepare_main_text,
)
from parser_modules.type_detection import is_explicit_optional_text


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

    main_text = prepare_main_text(row, description=description, item_type=item_type, separate_city=separate_city)
    if not row.get("is_optional") and is_explicit_optional_text(main_text):
        mark_optional_row(row, REASON_OPTIONAL_TEXT_PREFIX)

    apply_city_and_quality(row, main_text=main_text, description=description, item_type=item_type, current_day=current_day)
    apply_common_detail_fields(row, main_text)
    apply_hotel_fields(
        row,
        main_text=main_text,
        item_type=item_type,
        start_date=start_date,
        end_date=end_date,
        night_count_hint=night_count_hint,
    )
    apply_effective_type_and_routes(row)
    return finalize_row_quality_and_status(row, item_type=item_type)
