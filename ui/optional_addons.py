"""Optional add-on extraction and rendering helpers.

Optional rows are displayed outside the main included itinerary. This module
keeps optional-add-on collection/rendering separate from the general final-page
helpers so optional-specific rules do not leak into inclusion-page assembly.
"""

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_optional_row, is_self_arranged
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.content_engine import client_activity_description
from itinerary_generation.date_resolver import get_day_date_text
from itinerary_generation.titles import create_client_activity_title
from text_polish import format_duration_display, polish_title, strip_price_fragments
from ui.activity_inclusions import clean_activity_inclusion_items, get_fallback_activity_inclusions
from ui.render_helpers import (
    display_time,
    esc,
    get_activity_logistics,
    is_self_arranged_transport,
    normalize_list,
    render_list_items,
)


def create_optional_addons(parsed_rows):
    optional_rows = [row for row in parsed_rows if is_optional_row(row)]
    addons = []

    for row in optional_rows:
        category = str(row.get("group_tour_commercial_category") or "")
        if category == "single_supplement":
            # This is a commercial pricing condition, not a client experience.
            # It remains visible on the exclusions/commercial-notes page.
            continue
        row_type = str(row.get("group_tour_semantic_type") or get_row_type(row))
        activity_like = row_type in {"Activity", "Activity Upgrade"} or str(row.get("type", "")).lower() == "activity upgrade"
        title = create_client_activity_title(dict(row, effective_type="Activity")) if activity_like else row.get("title", "")
        title = polish_title(strip_price_fragments(str(title or row.get("title", "Optional add-on"))))
        city = polish_title(str(row.get("city", "")).strip())
        if activity_like and title.lower() in {"svolvær", "svolvaer", "svolaver", "svoalvaer"}:
            title = "Optional experience in Svolvær"
        time = display_time(row.get("time", ""))
        duration = strip_price_fragments(str(row.get("duration", "")).strip())
        includes = clean_activity_inclusion_items([clean_include_item(strip_price_fragments(item), title) for item in normalize_list(row.get("includes", []))], title)
        if activity_like and not includes:
            includes = get_fallback_activity_inclusions(dict(row, effective_type="Activity"))
        meeting_label, meeting_point = get_activity_logistics(row) if activity_like else ("", "")
        meeting_point = strip_price_fragments(meeting_point)

        if not title:
            continue

        if row_type in TRANSPORT_TYPES or is_self_arranged_transport(row):
            label = "Optional self-arranged travel" if is_self_arranged(row) else "Optional travel"
        elif row_type == "Transfer":
            label = "Optional transfer"
        elif activity_like:
            label = "Optional experience"
        else:
            label = "Optional add-on"

        description = ""
        if activity_like:
            description = client_activity_description(dict(row, effective_type="Activity", display_title=title))

        addons.append({
            "day": row.get("day", ""),
            "label": label,
            "title": title,
            "city": city,
            "date": get_day_date_text([row]) or row.get("start_date", ""),
            "time": time,
            "duration": duration,
            "meeting_label": meeting_label,
            "meeting_point": meeting_point,
            "includes": includes,
            "description": description,
        })

    return addons


def render_optional_addons_pages(optional_addons, items_per_page=8):
    if not optional_addons:
        return ""

    html_text = ""

    for start in range(0, len(optional_addons), items_per_page):
        chunk = optional_addons[start:start + items_per_page]
        html_text += f"""
        <div class="a4-page final-list-page optional-addons-page">
            <div class="final-page-title">Optional Experiences</div>
        """

        for addon in chunk:
            html_text += '<div class="activity-inclusion-block optional-addon-block">'
            heading_bits = [addon.get("title", ""), addon.get("date", "")]
            heading = " - ".join([bit for bit in heading_bits if bit])
            html_text += f'<div class="activity-inclusion-title">{esc(heading)}</div>'
            details = []
            if addon.get("time"):
                details.append(f'Time: {addon["time"]}')
            if addon.get("duration"):
                details.append(f'Duration: {format_duration_display(addon["duration"])}')
            if addon.get("meeting_point"):
                details.append(f'{addon.get("meeting_label") or "Meeting point"}: {addon["meeting_point"]}')
            if addon.get("description"):
                details.append(addon["description"])
            elif addon.get("includes"):
                details.append("Includes " + ", ".join(addon["includes"]))
            else:
                details.append("Available as an optional experience.")
            html_text += f'<div class="body-text muted-note">{esc(" ".join(details))}</div>'
            html_text += "</div>"

        html_text += "</div>"

    return html_text
