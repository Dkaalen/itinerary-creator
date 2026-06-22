"""Generated-day payload helpers for the visual editor."""

from itinerary_generation.common import get_primary_city
from itinerary_generation.day_text import create_day_intro, create_travel_route_label
from itinerary_generation.date_resolver import get_day_date_text
from itinerary_generation.editable_draft import day_by_id, first_block_html
from itinerary_generation.group_tour_rendering import (
    group_tour_day_city,
    group_tour_day_from_rows,
    group_tour_day_intro,
    group_tour_day_title,
)
from itinerary_generation.titles import create_day_title
from ui.day_blocks import build_day_blocks
from ui.render_helpers import get_detail_level_name
from visual_editor_component.editor_payload_images import build_day_image_payload


def build_payload_days(
    grouped_days,
    output_edits,
    stored_editor_draft,
    *,
    pictures_added: bool,
    image_matches,
    image_warnings_by_day,
):
    payload_days = []
    generated_days_values = []

    for day, rows in grouped_days.items():
        day_edits = (output_edits or {}).get("days", {}).get(day, {})
        typed_day = day_by_id(stored_editor_draft, day)
        group_tour_segment = group_tour_day_from_rows(rows)
        generated_group_tour_city = group_tour_day_city(rows) if group_tour_segment else ""
        generated_group_tour_title = group_tour_day_title(rows) if group_tour_segment else ""
        generated_group_tour_intro = group_tour_day_intro(rows) if group_tour_segment else ""
        generated_city = generated_group_tour_city or create_travel_route_label(rows) or get_primary_city(rows)
        generated_date = get_day_date_text(rows)
        generated_title = generated_group_tour_title or create_day_title(rows)
        generated_intro = generated_group_tour_intro or create_day_intro(rows, detail_level=get_detail_level_name(output_edits))
        city = typed_day.get("city") or day_edits.get("city") or generated_city
        image_obj = build_day_image_payload(
            day,
            rows,
            output_edits,
            pictures_added=pictures_added,
            image_matches=image_matches,
            image_warnings_by_day=image_warnings_by_day,
        )

        # Presence matters here: an intentionally emptied visual-editor block
        # must stay empty instead of falling back to regenerated content.
        typed_blocks_html = first_block_html(typed_day)
        generated_blocks_html = "".join(block["html"] for block in build_day_blocks(rows))
        if typed_blocks_html is not None:
            blocks_html = typed_blocks_html
        elif "blocks_html" in day_edits:
            blocks_html = day_edits.get("blocks_html", "")
        else:
            blocks_html = generated_blocks_html

        payload_days.append({
            "day": day,
            "label": typed_day.get("label") or day,
            "date": typed_day.get("date") or generated_date,
            "title": typed_day.get("title") or day_edits.get("title") or generated_title,
            "city": city,
            "intro": typed_day.get("intro") or day_edits.get("intro") or generated_intro,
            "blocks_html": blocks_html,
            "blocks": typed_day.get("blocks") or [{"block_id": "main", "kind": "day_content", "content_html": blocks_html}],
            "image": image_obj,
        })
        generated_days_values.append({
            "day": day,
            "label": day,
            "date": generated_date,
            "title": generated_title,
            "city": generated_city,
            "intro": generated_intro,
            "blocks_html": generated_blocks_html,
        })

    return payload_days, generated_days_values
