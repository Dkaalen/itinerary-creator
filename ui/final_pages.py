"""Final-page and inclusion-page rendering helpers."""

import re

from itinerary_generation.common import TRANSPORT_TYPES, get_row_type, is_self_arranged
from itinerary_generation.inclusions import clean_include_item
from itinerary_generation.titles import create_client_activity_title
from text_polish import format_duration_display, polish_inclusion_item, polish_inclusion_items
from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES
from ui.render_helpers import (
    display_time,
    esc,
    get_activity_logistics,
    is_self_arranged_transport,
    normalize_list,
    render_list_items,
    text_to_list,
)


def get_important_travel_notes(output_edits=None):
    if output_edits and output_edits.get("important_travel_notes_text"):
        return text_to_list(output_edits.get("important_travel_notes_text"))
    return DEFAULT_IMPORTANT_TRAVEL_NOTES


def get_fallback_activity_inclusions(row):
    """Create sensible client-facing inclusions when supplier text has no formal inclusion list."""

    title = create_client_activity_title(row) or row.get("title", "")
    source_items = normalize_list(row.get("includes", []))
    full_text = " ".join(
        [str(title), str(row.get("original_title", "")), str(row.get("details", ""))]
        + [str(item) for item in source_items]
    ).lower()

    if "tallin" in full_text or "tallinn" in full_text or title == "Day Trip to Tallinn":
        inclusions = []
        is_self_guided = bool(re.search(r"\bself[-\s]?guided\b", full_text, flags=re.IGNORECASE))
        if "port transfer" in full_text or "helsinki port" in full_text or "hotel pick" in full_text:
            inclusions.append("Helsinki port transfers")
        if "star class" in full_text:
            inclusions.append("Star Class ferry ticket")
        elif "ferry ticket" in full_text or "cruise ticket" in full_text or "day trip to tallinn" in str(title).lower():
            inclusions.append("Helsinki–Tallinn ferry crossing")
        if "old town" in full_text or "tallinn" in full_text or "tallin" in full_text:
            if is_self_guided:
                inclusions.append("Self-guided Old Town visit")
            elif "guided" in full_text:
                inclusions.append("Guided Old Town tour")
        if not inclusions:
            inclusions = ["Helsinki–Tallinn ferry crossing", "Time to explore Tallinn Old Town"]
        return inclusions

    if "essential oslo" in full_text or ("oslo" in full_text and "walking tour" in full_text):
        return ["Guided walking tour"]

    if "must-see bergen" in full_text or ("bergen" in full_text and "foot and boat" in full_text):
        return ["Guided walking tour", "Boat tour"]

    if "hop-on hop-off" in title.lower() or "hop on" in full_text or "hop-off" in full_text or "hop off" in full_text:
        return ["24-hour Hop-On Hop-Off bus ticket"]

    if "fløibanen" in full_text or "floibanen" in full_text:
        if "round" in full_text or "roundtrip" in full_text or "round trip" in full_text:
            return ["Round-trip Fløibanen ticket"]
        return ["Fløibanen ticket"]

    if "walking" in full_text and "canal" in full_text:
        return ["Guided walking tour", "Canal experience"]

    if "walking tour" in full_text or "guided" in full_text:
        return ["Guided experience"]

    if "ticket" in full_text:
        return ["Ticket"]

    return []


def prioritize_inline_inclusions(items, max_items=6):
    """Keep inline inclusions premium and compact.

    Day pages should show the most useful inclusions without turning into an
    appendix. Prefer logistics, guide, transport, tickets/entrance, meals and
    special equipment; drop low-value accounting items when space is limited.
    """

    clean_items = []
    for item in polish_inclusion_items(normalize_list(items)):
        if not item or item in clean_items:
            continue
        lower = item.lower()
        if lower in {"guided experience", "experience as described in the day-by-day itinerary"} and len(items) > 1:
            continue
        if any(marker in lower for marker in ["tax", "service fee", "goods and services"]):
            continue
        if "small group" in lower or ("max " in lower and "guest" in lower):
            continue
        # The title already tells the client they are visiting Santa Claus Village;
        # keep limited day-page inclusion space for more concrete inclusions like
        # snowmobiling, reindeer sleigh rides, winter equipment and lunch.
        if "fun visit to santa claus village" in lower:
            continue
        clean_items.append(item)

    def score(item):
        lower = item.lower()
        if "small group" in lower or ("max " in lower and "guest" in lower):
            return 99
        if "meteorological" in lower or "observation" in lower:
            return 98
        if "pick" in lower or "drop" in lower or "transfer" in lower:
            return 0
        if "reindeer" in lower or "snowmobile" in lower or "santa claus" in lower or "husky" in lower:
            return 1
        if any(marker in lower for marker in ["thermal", "overall", "winter clothes", "winter equipment", "equipment", "boots", "gloves", "balaclava", "helmet", "survival suit", "floating suit"]):
            return 2
        if "meal" in lower or "lunch" in lower or "dinner" in lower or "drink" in lower or "snack" in lower or "cookies" in lower or "barbecue" in lower or "bbq" in lower or "berry juice" in lower:
            return 3
        if "hike" in lower or "canyon" in lower or "waterfall" in lower:
            return 4
        if "photo" in lower or "camera" in lower or "dslr" in lower:
            return 5
        if "ticket" in lower or "entrance" in lower or "ferry" in lower or "certificate" in lower:
            return 6
        if "guide" in lower or "guided" in lower or "certified" in lower:
            return 7
        if "transport" in lower or "coach" in lower or "minivan" in lower or "bus" in lower:
            return 8
        return 10

    ordered = sorted(enumerate(clean_items), key=lambda pair: (score(pair[1]), pair[0]))
    selected = [item for _, item in ordered[:max_items]]
    # Restore original order among selected items so the client-facing flow feels natural.
    return [item for item in clean_items if item in selected]


def looks_like_descriptive_prose(text):
    lower = str(text or "").lower()
    prose_markers = [
        "tour gives",
        "take a stroll",
        "listen to",
        "make sense",
        "to top it all",
        "waterworld",
        "best way to understand",
        "explore bergen from",
        "historic city streets",
    ]
    return len(str(text or "")) > 95 and any(marker in lower for marker in prose_markers)


def clean_activity_inclusion_items(items, title=""):
    clean_items = []
    for item in normalize_list(items):
        text = polish_inclusion_item(str(item).strip(), title)
        lower = text.lower().strip(":? ")

        text = re.split(r"\s+-\s+(?:Description|Overview)\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:")
        lower = text.lower().strip(":? ")

        if lower in {"what's included", "what’s included", "includes", "included", "description", "overview"}:
            continue

        # Avoid long overview prose on the inclusion page.
        if looks_like_descriptive_prose(text):
            continue
        if len(text) > 150 and "included" not in lower:
            continue

        text = polish_inclusion_item(clean_include_item(text, title), title)
        if text and text not in clean_items:
            clean_items.append(text)

    clean_items = polish_inclusion_items(clean_items, title)
    if not clean_items or all(looks_like_descriptive_prose(item) for item in clean_items):
        return []
    return clean_items


def create_optional_addons(parsed_rows):
    optional_rows = [row for row in parsed_rows if row.get("is_optional")]
    addons = []

    for row in optional_rows:
        row_type = get_row_type(row)
        title = create_client_activity_title(row) if row_type == "Activity" else row.get("title", "")
        title = str(title or row.get("title", "Optional add-on")).strip()
        city = str(row.get("city", "")).strip()
        if row_type == "Activity" and title.lower() in {"svolvær", "svolvaer", "svolaver", "svoalvaer"}:
            title = "Optional experience in Svolvær"
        time = display_time(row.get("time", ""))
        duration = str(row.get("duration", "")).strip()
        includes = polish_inclusion_items([clean_include_item(item, title) for item in normalize_list(row.get("includes", []))], title)
        if row_type == "Activity" and not includes:
            includes = get_fallback_activity_inclusions(row)
        meeting_label, meeting_point = get_activity_logistics(row) if row_type == "Activity" else ("", "")

        if not title:
            continue

        if row_type in TRANSPORT_TYPES or is_self_arranged_transport(row):
            label = "Optional self-arranged travel" if is_self_arranged(row) else "Optional travel"
        elif row_type == "Transfer":
            label = "Optional transfer"
        elif row_type == "Activity":
            label = "Optional experience"
        else:
            label = "Optional add-on"

        addons.append({
            "day": row.get("day", ""),
            "label": label,
            "title": title,
            "city": city,
            "time": time,
            "duration": duration,
            "meeting_label": meeting_label,
            "meeting_point": meeting_point,
            "includes": includes,
        })

    return addons


def render_optional_addons_pages(optional_addons, items_per_page=8):
    if not optional_addons:
        return ""

    html_text = ""

    for start in range(0, len(optional_addons), items_per_page):
        chunk = optional_addons[start:start + items_per_page]
        continued = "" if start == 0 else " continued"
        html_text += f'''
        <div class="a4-page final-list-page optional-addons-page">
            <div class="final-page-title">Optional add-ons{continued}</div>
        '''

        for addon in chunk:
            html_text += '<div class="activity-inclusion-block optional-addon-block">'
            heading_bits = [addon.get("day", ""), addon.get("title", "")]
            heading = " — ".join([bit for bit in heading_bits if bit])
            html_text += f'<div class="activity-inclusion-title">{esc(heading)}</div>'
            html_text += f'<div class="body-text"><span class="meta-label">Type:</span> {esc(addon.get("label", "Optional add-on"))}</div>'

            if addon.get("city"):
                html_text += f'<div class="body-text"><span class="meta-label">Location:</span> {esc(addon["city"])}</div>'
            if addon.get("time"):
                html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(addon["time"])}</div>'
            if addon.get("duration"):
                html_text += f'<div class="body-text"><span class="meta-label">Duration:</span> {esc(format_duration_display(addon["duration"]))}</div>'
            if addon.get("meeting_point"):
                html_text += f'<div class="body-text"><span class="meta-label">{esc(addon.get("meeting_label") or "Meeting point")}:</span> {esc(addon["meeting_point"])}</div>'
            if addon.get("includes"):
                html_text += '<div class="section-title small-section">Includes</div>'
                html_text += render_list_items(addon["includes"], class_name="final-list")

            html_text += "</div>"

        html_text += "</div>"

    return html_text
