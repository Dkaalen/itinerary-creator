"""Day-page rendering for optional itinerary rows."""

from __future__ import annotations

from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from text_polish import polish_client_text, polish_title, strip_price_fragments
from ui.render_helpers import display_time_with_duration, esc, get_activity_logistics


def _optional_title(row: dict) -> str:
    title = create_client_activity_title(row) if (row.get("effective_type") or row.get("type")) == "Activity" else row.get("title", "")
    title = normalize_client_day_title(title or row.get("title") or "Optional experience", row)
    return polish_title(strip_price_fragments(title)) or "Optional experience"


def build_optional_day_block(row: dict) -> dict:
    """Render an optional row inside its itinerary day without marking it included."""

    row_id = row.get("row_id", "")
    row_type = row.get("effective_type") or row.get("type", "")
    title = _optional_title(row)
    time_display = display_time_with_duration(row.get("time", ""), row.get("duration", ""))
    meeting_label, meeting_point = get_activity_logistics(row) if row_type == "Activity" else ("", "")

    description = ""
    if row_type == "Activity":
        block = canonical_activity_block(dict(row, display_title=title))
        description = block.description
    if not description:
        description = polish_client_text(row.get("description", "") or row.get("details", ""))

    html_text = f'<div class="content-block optional-experience-block" data-row-id="{esc(row_id)}">'
    html_text += '<div class="section-title">Optional Experience</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'
    if time_display:
        html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(time_display)}</div>'
    if meeting_point:
        html_text += f'<div class="body-text"><span class="meta-label">{esc(meeting_label or "Meeting point")}:</span> {esc(strip_price_fragments(meeting_point))}</div>'
    if description:
        html_text += f'<div class="body-text muted-note">{esc(description)}</div>'
    html_text += '</div>'
    return {"kind": "optional_experience", "row_id": row_id, "html": html_text}
