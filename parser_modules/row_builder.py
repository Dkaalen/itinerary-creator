"""Parser row construction helpers."""

from parser_modules.commercial_status import initial_commercial_state
from parser_modules.common import clean_space


def build_base_row(
    *,
    raw_line,
    line_number,
    row_id,
    is_optional,
    current_day,
    item_type,
    original_item_type,
    start_date,
    end_date,
    description,
):
    commercial_status, commercial_reason = initial_commercial_state(is_optional)
    return {
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
