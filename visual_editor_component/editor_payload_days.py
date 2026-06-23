"""Generated-day payload helpers for the visual editor."""

from itinerary_generation.day_content_resolver import resolve_day_content
from itinerary_generation.editable_draft import day_by_id
from itinerary_generation.generated_ownership import resolve_blocks_html
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
    detail_level = get_detail_level_name(output_edits)

    for day, rows in grouped_days.items():
        day_edits = (output_edits or {}).get("days", {}).get(day, {})
        typed_day = day_by_id(stored_editor_draft, day)
        resolved = resolve_day_content(
            day,
            rows,
            output_edits=output_edits,
            typed_day=typed_day,
            detail_level=detail_level,
        )
        image_obj = build_day_image_payload(
            day,
            rows,
            output_edits,
            pictures_added=pictures_added,
            image_matches=image_matches,
            image_warnings_by_day=image_warnings_by_day,
        )

        generated_blocks_html = "".join(block["html"] for block in build_day_blocks(rows))
        resolved_blocks = resolve_blocks_html(
            day_edits=day_edits if isinstance(day_edits, dict) else {},
            typed_day=typed_day if isinstance(typed_day, dict) else {},
            generated_blocks_html=generated_blocks_html,
        )

        day_payload = {
            "day": day,
            "label": typed_day.get("label") or resolved.label or day,
            "date": resolved.date,
            "title": resolved.title,
            "city": resolved.city,
            "intro": resolved.intro,
            "intro_generated_value": resolved.generated_intro,
            "intro_generator_version": resolved.intro_metadata["intro_generator_version"],
            "intro_source_signature": resolved.source_signature,
            "intro_manual_override": resolved.intro_ownership.manual_override,
            "blocks_html": resolved_blocks.html,
            "blocks_html_generated_value": generated_blocks_html,
            "blocks_html_generator_version": resolved_blocks.metadata()["blocks_html_generator_version"],
            "blocks_manual_override": resolved_blocks.manual_override,
            "blocks": typed_day.get("blocks") or [{"block_id": "main", "kind": "day_content", "content_html": resolved_blocks.html}],
            "image": image_obj,
        }
        payload_days.append(day_payload)
        generated_days_values.append({
            "day": day,
            "label": day,
            "date": resolved.generated_date,
            "title": resolved.generated_title,
            "city": resolved.generated_city,
            "intro": resolved.generated_intro,
            "blocks_html": generated_blocks_html,
        })

    return payload_days, generated_days_values
