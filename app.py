from pathlib import Path
import copy
import html
import json
import re

import streamlit as st
import diagnostics
from itinerary_parser import parse_itinerary, normalize_time_text
from pdf_exporter import export_html_to_pdf
from generator import (
    TRANSPORT_TYPES,
    create_client_activity_title,
    create_day_intro,
    create_day_title,
    create_destinations_line,
    create_journey_arc,
    create_trip_glance,
    create_trip_subtitle,
    create_trip_title,
    create_whats_included,
    create_whats_not_included,
    clean_include_item,
    get_primary_city,
    get_row_type,
    group_rows_by_day,
    is_self_arranged,
)


APP_VERSION = "2026-05-19 v30-review-assistant-detail-level"


st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide",
)


COLOR_PRESETS = {
    "Classic Agent": {
        "page_bg": "#f4efe8",
        "preview_bg": "#11151b",
        "ink": "#1f3446",
        "body": "#2f2f2f",
        "muted": "#7b746c",
        "line": "#d8cec2",
        "card": "rgba(255, 255, 255, 0.34)",
        "accent": "#1f3446",
    },
    "Booknordics B2C": {
        "page_bg": "#F7F9FB",
        "preview_bg": "#07111F",
        "ink": "#111827",
        "body": "#1F2937",
        "muted": "#64748B",
        "line": "#D9E1EA",
        "card": "rgba(255, 255, 255, 0.82)",
        "accent": "#F2055C",
    },
}

PRESET_ORDER = list(COLOR_PRESETS.keys())

DETAIL_LEVELS = [
    "Elegant concise",
    "Standard client itinerary",
    "Rich descriptive",
]


st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; }
        div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 { margin-top: 0.25rem; }
        .app-hero {
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 18px;
            padding: 1.1rem 1.25rem;
            background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
            margin-bottom: 1rem;
        }
        .app-hero h1 { margin-bottom: 0.2rem; }
        .app-hero p { margin-bottom: 0; opacity: 0.82; }
        .section-card {
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 16px;
            padding: 1rem;
            margin: 0.5rem 0 1rem 0;
            background: rgba(255,255,255,0.025);
        }
        .workflow-note {
            font-size: 0.9rem;
            opacity: 0.76;
            margin-bottom: 0.7rem;
        }
        .sidebar-pill {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 999px;
            padding: 0.28rem 0.55rem;
            margin: 0.18rem 0;
            font-size: 0.82rem;
            background: rgba(255,255,255,0.035);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def esc(value):
    return html.escape(str(value or ""), quote=True)


def normalize_list(items):
    if not items:
        return []

    if isinstance(items, list):
        return [str(item).strip() for item in items if item and str(item).strip()]

    if isinstance(items, str):
        return [item.strip() for item in items.split(",") if item.strip()]

    return []


def list_to_text(items):
    return "\n".join(normalize_list(items))


def text_to_list(value):
    if not value:
        return []

    clean_items = []

    for line in str(value).splitlines():
        item = line.strip()
        item = item.lstrip("•").lstrip("-").strip()

        if item:
            clean_items.append(item)

    return clean_items




def display_time(value):
    return normalize_time_text(value)



def get_activity_logistics(row):
    """Return a practical meeting/pick-up line for the day-by-day block."""

    meeting_point = str(row.get("meeting_point") or "").strip()
    if meeting_point:
        return "Meeting point", meeting_point

    for item in normalize_list(row.get("includes", [])):
        item_text = str(item).strip()
        lower = item_text.lower()

        if "pick-up/drop-off" in lower or "pickup/drop-off" in lower or "pick up/drop-off" in lower:
            value = re.sub(r"^(pick[- ]?up/drop[- ]?off\s*)", "", item_text, flags=re.IGNORECASE).strip(" :.-")
            return "Pick-up/drop-off", value or item_text

        if lower.startswith("departure from") or "drop-off" in lower or "drop off" in lower:
            return "Departure/drop-off", item_text

    return "", ""

def render_list_items(items, class_name="detail-list"):
    clean_items = normalize_list(items)

    if not clean_items:
        return ""

    html_text = f'<ul class="{esc(class_name)}">'

    for item in clean_items:
        html_text += f"<li>{esc(item)}</li>"

    html_text += "</ul>"

    return html_text


def get_time_period(time_text):
    if not time_text:
        return "Featured experience"

    text = time_text.lower()
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)

    if not match:
        # 24-hour format support.
        match_24 = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
        if not match_24:
            return "Featured experience"

        hour = int(match_24.group(1))
    else:
        hour = int(match.group(1))
        period = match.group(3)

        if period == "pm" and hour != 12:
            hour += 12

        if period == "am" and hour == 12:
            hour = 0

    if hour < 12:
        return "Morning Experience"

    if 12 <= hour < 17:
        return "Afternoon Experience"

    return "Evening Experience"


def plural_nights(value):
    value = str(value or "").strip()

    if not value:
        return ""

    if value == "1":
        return "1 night"

    return f"{value} nights"


def meal_phrase(value):
    value = str(value or "").strip()

    if not value:
        return ""

    lower = value.lower()

    if lower.startswith("with ") or lower.startswith("without "):
        return value

    if lower in ["breakfast", "dinner", "half board", "full board", "breakfast and dinner"]:
        return f"with {lower}"

    return f"with {value}"




def get_color_preset_name(output_edits=None):
    name = (output_edits or {}).get("color_preset") or st.session_state.get("color_preset", "Classic Agent")
    if name not in COLOR_PRESETS:
        return "Classic Agent"
    return name


def get_color_preset(output_edits=None):
    return COLOR_PRESETS[get_color_preset_name(output_edits)]


def is_self_arranged_transport(row):
    return get_row_type(row) in TRANSPORT_TYPES and is_self_arranged(row)


def get_activity_description(row, detail_level=None):
    detail_level = detail_level or get_detail_level_name()
    title = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    city = str(row.get("city", "")).strip().lower()

    if "fjellheisen" in title or "round trip ticket" in title:
        if detail_level == "Elegant concise":
            return "Ride Fjellheisen for panoramic views over Tromsø."
        if detail_level == "Rich descriptive":
            return "Ride the Fjellheisen cable car for sweeping views over Tromsø, the surrounding islands, fjords, and mountain scenery."
        return "Enjoy panoramic views over Tromsø, the surrounding islands, fjords, and mountains."

    if "lofoten" in title and "trollfjord" in title:
        if detail_level == "Elegant concise":
            return "Travel through Lofoten by land and sea, including Trollfjord scenery."
        if detail_level == "Rich descriptive":
            return "Experience Lofoten by land and sea, with time around Stokmarknes and a scenic cruise into the dramatic Trollfjord landscape."
        return "Travel through Lofoten by land and sea, with time around Stokmarknes and a cruise into the dramatic Trollfjord."

    if "city walking" in title and "canal" in title and "copenhagen" in title:
        if detail_level == "Elegant concise":
            return "Explore Copenhagen on foot and by canal with a local host."
        if detail_level == "Rich descriptive":
            return "Explore central Copenhagen with a local host, combining city landmarks, local stories, and a scenic canal experience."
        return "Explore central Copenhagen on foot with a local host, including key landmarks and a scenic canal experience."

    if "essential oslo" in title:
        if detail_level == "Elegant concise":
            return "Explore central Oslo on foot with a local guide."
        if detail_level == "Rich descriptive":
            return "Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital."
        return "Explore central Oslo on foot with a local guide, including key landmarks around the city center."

    if "guided walking tour" in title:
        if "copenhagen" in city or "copenhagen" in title:
            if detail_level == "Elegant concise":
                return "Explore central Copenhagen on foot with a local guide."
            if detail_level == "Rich descriptive":
                return "Explore central Copenhagen on foot with a local guide, with time for local stories, major landmarks, and the atmosphere of the city."
            return "Explore central Copenhagen on foot with a local guide, with time for local stories and key city landmarks."
        if "oslo" in city or "oslo" in title:
            if detail_level == "Elegant concise":
                return "Explore central Oslo on foot with a local guide."
            if detail_level == "Rich descriptive":
                return "Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital."
            return "Explore central Oslo on foot with a local guide, including key landmarks around the city center."

    if "must-see bergen" in title or ("foot and boat" in title and "bergen" in title):
        if detail_level == "Elegant concise":
            return "Explore Bergen on foot and by boat."
        if detail_level == "Rich descriptive":
            return "Explore Bergen from two perspectives: on foot through the historic city streets and by boat from the surrounding waters."
        return "Explore Bergen on foot and by boat, combining historic city streets with a scenic perspective from the water."

    if "hop on" in title or "hop-on" in title or "hop off" in title or "hop-off" in title:
        if detail_level == "Rich descriptive":
            return "Use your flexible ticket to explore the city at your own pace, choosing the stops and sights that suit your day best."
        return "Use your flexible ticket to explore the city at your own pace."

    if "tallinn" in title:
        if detail_level == "Elegant concise":
            return "Travel from Helsinki to Tallinn and explore the Old Town."
        if detail_level == "Rich descriptive":
            return "Travel from Helsinki to Tallinn and enjoy time in the atmospheric Old Town before returning to Helsinki."
        return "Travel from Helsinki to Tallinn and enjoy time to explore the historic Old Town before returning to Helsinki."

    return ""

def is_self_transfer(row):
    row_type = get_row_type(row)
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()

    return row_type == "Transfer" and "self transfer" in text


def build_activity_block(row):
    title = row.get("title", "")
    time = row.get("time", "")
    duration = row.get("duration", "")
    meeting_label, meeting_point = get_activity_logistics(row)
    end_point = row.get("end_point", "")
    notable_sights = normalize_list(row.get("notable_sights", []))
    description = row.get("client_description") or get_activity_description(row)

    html_text = f'<div class="content-block activity-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += f'<div class="section-title">{esc(get_time_period(time))}</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if time:
        html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(display_time(time))}</div>'

    if duration:
        duration_label = "Cruise duration" if "cruise" in duration.lower() else "Duration"
        clean_duration = re.sub(r"^cruise duration\s*:?\s*", "", str(duration), flags=re.IGNORECASE).strip()
        html_text += f'<div class="body-text"><span class="meta-label">{esc(duration_label)}:</span> {esc(clean_duration)}</div>'

    if meeting_point:
        html_text += f'<div class="body-text"><span class="meta-label">{esc(meeting_label)}:</span> {esc(meeting_point)}</div>'

    if end_point:
        html_text += f'<div class="body-text"><span class="meta-label">End point:</span> {esc(end_point)}</div>'

    if description:
        html_text += f'<div class="body-text muted-note">{esc(description)}</div>'

    if notable_sights:
        html_text += '<div class="section-title small-section">Notable sights</div>'
        html_text += render_list_items(notable_sights)

    html_text += "</div>"

    return {
        "kind": "activity",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }

def build_transport_block(row):
    title = row.get("title", "")
    time = row.get("time", "")
    duration = row.get("duration", "")
    includes = [clean_include_item(item, title) for item in normalize_list(row.get("includes", []))]
    luggage_included = clean_include_item(row.get("luggage_included", ""), title)

    html_text = f'<div class="content-block transport-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Travel today</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if time:
        html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(display_time(time))}</div>'

    if duration:
        clean_duration = re.sub(r"^duration\s*:?\s*", "", str(duration), flags=re.IGNORECASE).strip()
        html_text += f'<div class="body-text"><span class="meta-label">Duration:</span> {esc(clean_duration)}</div>'

    if luggage_included:
        html_text += f'<div class="body-text"><span class="meta-label">Luggage included:</span> {esc(luggage_included)}</div>'

    if includes:
        html_text += '<div class="section-title small-section">Includes</div>'
        html_text += render_list_items(includes)

    html_text += "</div>"

    return {
        "kind": "transport",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }

def build_self_transfer_block(row, title_override=None):
    title = title_override or row.get("title", "")
    city = row.get("city", "")

    html_text = f'<div class="content-block self-transfer-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Self-guided transfer</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if city:
        html_text += f'<div class="body-text"><span class="meta-label">Location:</span> {esc(city)}</div>'

    html_text += (
        '<div class="body-text muted-note">'
        'This is a self-guided transfer, so please make your own way between these points. '
        'Transfer costs are not included unless specifically stated elsewhere in the itinerary.'
        '</div>'
    )
    html_text += "</div>"

    return {
        "kind": "self_transfer",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }


def build_self_arranged_travel_block(row, title_override=None):
    title = title_override or row.get("title", "")
    city = row.get("city", "")
    row_type = get_row_type(row).lower()

    if row_type == "flight":
        note = "This flight is self-arranged and not included in the package price unless specifically stated."
    else:
        note = "This travel segment is self-arranged and not included in the package price unless specifically stated."

    html_text = f'<div class="content-block self-arranged-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Self-arranged travel</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if city:
        html_text += f'<div class="body-text"><span class="meta-label">Destination:</span> {esc(city)}</div>'

    html_text += f'<div class="body-text muted-note">{esc(note)}</div>'
    html_text += "</div>"

    return {
        "kind": "self_arranged_travel",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }

def build_accommodation_block(row):
    hotel_name = str(row.get("hotel_name") or row.get("title") or "Accommodation as listed").strip()
    nights = plural_nights(row.get("hotel_nights", ""))
    room_category = str(row.get("room_category") or "").strip()
    meal = meal_phrase(row.get("meal_plan", ""))

    accommodation_line = f"{hotel_name} or similar"

    if nights:
        accommodation_line += f" for {nights}"

    room_line_parts = []

    if room_category:
        room_line_parts.append(f"Room category: {room_category}")

    if meal:
        if room_line_parts:
            room_line_parts[-1] += f", {meal}"
        else:
            room_line_parts.append(meal.capitalize())

    html_text = f'<div class="content-block accommodation-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Accommodation</div>'
    html_text += f'<div class="body-text strong-line">{esc(accommodation_line)}</div>'

    for line in room_line_parts:
        html_text += f'<div class="body-text">{esc(line)}</div>'

    html_text += "</div>"

    return {
        "kind": "accommodation",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }


def build_leisure_block(row=None):
    row_id = row.get("row_id", "") if row else ""

    html_text = f'<div class="content-block leisure-block" data-row-id="{esc(row_id)}">'
    html_text += '<div class="section-title">Your free time</div>'
    html_text += (
        '<div class="body-text">'
        'Time at leisure is included so the day does not feel overfilled. '
        'Use this space to settle in, explore nearby streets, enjoy a relaxed meal, '
        'or simply take the destination at your own pace.'
        '</div>'
    )
    html_text += "</div>"

    return {
        "kind": "leisure",
        "row_id": row_id,
        "html": html_text,
    }


def build_departure_block(row):
    title = row.get("title", "") or "Departure home"

    html_text = f'<div class="content-block departure-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Departure</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'
    html_text += '</div>'

    return {
        "kind": "departure",
        "row_id": row.get("row_id", ""),
        "html": html_text,
    }


def build_included_today_block(items):
    clean_items = normalize_list(items)

    if not clean_items:
        return None

    html_text = '<div class="content-block included-block">'
    html_text += '<div class="section-title">Included today</div>'
    html_text += render_list_items(clean_items)
    html_text += "</div>"

    return {
        "kind": "included",
        "row_id": "included-today",
        "html": html_text,
    }


def build_day_blocks(rows):
    blocks = []
    included_items = []

    def flush_included():
        nonlocal included_items
        included_block = build_included_today_block(included_items)
        if included_block:
            blocks.append(included_block)
        included_items = []

    for row in rows:
        row_type = get_row_type(row)
        title = row.get("title", "")

        if row_type == "Transfer" and is_self_transfer(row):
            flush_included()
            blocks.append(build_self_transfer_block(row))

        elif row_type in TRANSPORT_TYPES and is_self_arranged(row):
            flush_included()
            blocks.append(build_self_arranged_travel_block(row, title_override=title))

        elif row_type == "Departure":
            flush_included()
            blocks.append(build_departure_block(row))

        elif row_type == "Hotel":
            flush_included()
            blocks.append(build_accommodation_block(row))

        elif row_type == "Arrival":
            if title:
                included_items.append(title)

        elif row_type == "Transfer":
            if title:
                included_items.append(title)

        elif row_type in TRANSPORT_TYPES:
            flush_included()
            blocks.append(build_transport_block(row))

        elif row_type == "Activity":
            flush_included()
            blocks.append(build_activity_block(row))

        elif row_type == "Leisure":
            flush_included()
            blocks.append(build_leisure_block(row))

        elif title:
            included_items.append(title)

    flush_included()

    return blocks

def render_day_pages(day, rows, output_edits=None):
    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    day_title = day_edits.get("title") or create_day_title(rows)
    detail_level = get_detail_level_name(output_edits)
    day_intro = day_edits.get("intro") or create_day_intro(rows, detail_level=detail_level)
    city = day_edits.get("city") or get_primary_city(rows)
    blocks = build_day_blocks(rows)

    html_text = f"""
        <div class="a4-page day-page" data-day="{esc(day)}">
            <div class="day-label">{esc(day)}</div>
            <div class="day-title">{esc(day_title)}</div>
            <div class="city">{esc(city)}</div>
            <div class="intro">{esc(day_intro)}</div>
    """

    for block in blocks:
        html_text += block["html"]

    html_text += "</div>"

    return html_text


def render_split_list_pages(title, items, items_per_page=24):
    html_text = ""
    clean_items = normalize_list(items)

    if not clean_items:
        return ""

    for start in range(0, len(clean_items), items_per_page):
        chunk = clean_items[start:start + items_per_page]
        continued = "" if start == 0 else " continued"

        html_text += f"""
        <div class="a4-page final-list-page">
            <div class="final-page-title">{esc(title)}{continued}</div>
            {render_list_items(chunk, class_name="final-list")}
        </div>
        """

    return html_text



def get_fallback_activity_inclusions(row):
    """Create sensible client-facing inclusions when supplier text has no formal inclusion list."""

    title = create_client_activity_title(row) or row.get("title", "")
    full_text = f'{title} {row.get("original_title", "")} {row.get("details", "")}'.lower()

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

    return ["Experience as described in the day-by-day itinerary"]


def clean_activity_inclusion_items(items, title=""):
    clean_items = []
    for item in normalize_list(items):
        text = str(item).strip()
        lower = text.lower().strip(":? ")

        if lower in {"what's included", "what’s included", "includes", "included"}:
            continue

        # Avoid long overview prose on the inclusion page.
        if len(text) > 150 and "included" not in lower:
            continue

        text = clean_include_item(text, title)
        if text and text not in clean_items:
            clean_items.append(text)

    return clean_items

def create_activity_inclusions(parsed_rows):
    activity_sections = []

    for row in parsed_rows:
        if get_row_type(row) != "Activity":
            continue

        title = create_client_activity_title(row) or row.get("title", "")
        title = str(title).strip()
        includes = clean_activity_inclusion_items(row.get("includes", []), title)

        # Every activity should be represented on this page. If the supplier
        # text does not contain a formal inclusion list, use a conservative
        # fallback based on the activity type.
        if not includes:
            includes = get_fallback_activity_inclusions(row)

        if not title or not includes:
            continue

        activity_sections.append({
            "title": title,
            "includes": includes,
            "is_optional": bool(row.get("is_optional")),
        })

    return activity_sections


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
        includes = [clean_include_item(item, title) for item in normalize_list(row.get("includes", []))]
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

def estimate_activity_inclusion_units(section):
    """Estimate how much vertical space an inclusion section needs on an A4 page.

    The goal is to avoid the old fixed-count split where six compact sections
    became five sections on one page and a nearly empty continued page. The
    estimate intentionally stays conservative for long bullet text, while still
    allowing compact ticket-style sections to share a page.
    """

    includes = normalize_list(section.get("includes", []))
    title_units = 2.4
    bullet_units = 0

    for item in includes:
        # One normal bullet line plus extra allowance for wrapped text.
        bullet_units += 1.0 + max(0, (len(str(item)) - 78) / 78)

    # Small spacing between activity sections.
    return title_units + bullet_units + 0.8


def chunk_activity_inclusions(activity_sections, max_units=34):
    chunks = []
    current_chunk = []
    current_units = 0

    for section in activity_sections:
        section_units = estimate_activity_inclusion_units(section)

        if current_chunk and current_units + section_units > max_units:
            chunks.append(current_chunk)
            current_chunk = [section]
            current_units = section_units
        else:
            current_chunk.append(section)
            current_units += section_units

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def render_activity_inclusions_pages(activity_sections):
    if not activity_sections:
        return ""

    html_text = ""
    chunks = chunk_activity_inclusions(activity_sections)

    for index, chunk in enumerate(chunks):
        continued = "" if index == 0 else " continued"

        html_text += f"""
        <div class="a4-page final-list-page activity-inclusions-page">
            <div class="final-page-title">Activity inclusions{continued}</div>
        """

        for section in chunk:
            html_text += '<div class="activity-inclusion-block">'
            optional_label = "Optional: " if section.get("is_optional") else ""
            html_text += f'<div class="activity-inclusion-title">{esc(optional_label + section["title"])}</div>'
            html_text += render_list_items(section["includes"], class_name="final-list")
            html_text += "</div>"

        html_text += "</div>"

    return html_text


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
                html_text += f'<div class="body-text"><span class="meta-label">Duration:</span> {esc(addon["duration"])}</div>'
            if addon.get("meeting_point"):
                html_text += f'<div class="body-text"><span class="meta-label">{esc(addon.get("meeting_label") or "Meeting point")}:</span> {esc(addon["meeting_point"])}</div>'
            if addon.get("includes"):
                html_text += '<div class="section-title small-section">Includes</div>'
                html_text += render_list_items(addon["includes"], class_name="final-list")

            html_text += "</div>"

        html_text += "</div>"

    return html_text


def make_output_edit_state(parsed_rows, grouped_days):
    edits = {
        "trip_title": create_trip_title(parsed_rows, grouped_days),
        "trip_subtitle": create_trip_subtitle(parsed_rows, grouped_days),
        "destinations_line": create_destinations_line(parsed_rows),
        "color_preset": st.session_state.get("color_preset", "Classic Agent"),
        "detail_level": st.session_state.get("detail_level", "Standard client itinerary"),
        "days": {},
        "rows": {},
        "whats_included_text": list_to_text(create_whats_included(parsed_rows, grouped_days)),
        "whats_not_included_text": list_to_text(create_whats_not_included()),
    }

    for day, rows in grouped_days.items():
        edits["days"][day] = {
            "title": create_day_title(rows),
            "intro": create_day_intro(rows, detail_level=edits["detail_level"]),
            "city": get_primary_city(rows),
        }

        for row in rows:
            row_id = row.get("row_id") or f'line_{row.get("line_number", len(edits["rows"]))}'
            title = create_client_activity_title(row) if get_row_type(row) == "Activity" else row.get("title", "")

            edits["rows"][row_id] = {
                "title": title,
                "city": row.get("city", ""),
                "time": row.get("time", ""),
                "duration": row.get("duration", ""),
                "client_description": row.get("client_description") or get_activity_description(row, edits["detail_level"]),
                "meeting_point": row.get("meeting_point", ""),
                "end_point": row.get("end_point", ""),
                "luggage_included": row.get("luggage_included", ""),
                "hotel_name": row.get("hotel_name", ""),
                "hotel_nights": row.get("hotel_nights", ""),
                "room_category": row.get("room_category", ""),
                "meal_plan": row.get("meal_plan", ""),
                "notable_sights_text": list_to_text(row.get("notable_sights", [])),
                "includes_text": list_to_text(row.get("includes", [])),
            }

    return edits


def apply_output_edits(parsed_rows, output_edits):
    edited_rows = copy.deepcopy(parsed_rows)
    row_edits = (output_edits or {}).get("rows", {})

    for row in edited_rows:
        row["original_title"] = row.get("original_title") or row.get("title", "")
        row_id = row.get("row_id") or f'line_{row.get("line_number", "")}'
        edits = row_edits.get(row_id, {})

        for key in [
            "title",
            "city",
            "time",
            "duration",
            "client_description",
            "meeting_point",
            "end_point",
            "luggage_included",
            "hotel_name",
            "hotel_nights",
            "room_category",
            "meal_plan",
        ]:
            if key in edits:
                row[key] = edits.get(key, "")

        if "notable_sights_text" in edits:
            row["notable_sights"] = text_to_list(edits.get("notable_sights_text", ""))

        if "includes_text" in edits:
            row["includes"] = text_to_list(edits.get("includes_text", ""))

    return edited_rows


def get_duplicate_count(raw_text_value, parsed_rows=None):
    raw_rows = [
        line for line in raw_text_value.splitlines()
        if "day " in line.strip().lower()
    ]

    parsed_count = len(parsed_rows) if parsed_rows is not None else len(parse_itinerary(raw_text_value))

    return max(len(raw_rows) - parsed_count, 0)


def get_overflow_warnings(grouped_days):
    warnings = []

    for day, rows in grouped_days.items():
        activity_count = sum(1 for row in rows if get_row_type(row) == "Activity")
        block_count = len(rows)
        long_text_score = sum(len(str(row.get("title", ""))) for row in rows)

        if block_count >= 7 or activity_count >= 3 or long_text_score > 520:
            warnings.append(f"{day} may be too full for one A4 page. Review the editable output before exporting.")

    return warnings


def render_output_editor(parsed_rows, grouped_days, output_edits):
    st.markdown('<div class="workflow-note">Edit the generated output here. The raw Excel input above is not changed.</div>', unsafe_allow_html=True)

    reset_col, help_col = st.columns([1, 3])
    with reset_col:
        if st.button("Reset edits", help="Return the editable fields to the generated text."):
            st.session_state.output_edits = make_output_edit_state(
                st.session_state.parsed_rows,
                group_rows_by_day(st.session_state.parsed_rows),
            )
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Needs refresh"
            st.rerun()
    with help_col:
        st.caption("Tip: edit only the fields you need. The preview and export files update from these fields automatically.")

    with st.expander("Cover and summary pages", expanded=False):
        output_edits["trip_title"] = st.text_input(
            "Cover title",
            value=output_edits.get("trip_title", ""),
            key="edit_trip_title",
        )
        output_edits["trip_subtitle"] = st.text_area(
            "Cover subtitle",
            value=output_edits.get("trip_subtitle", ""),
            height=80,
            key="edit_trip_subtitle",
        )
        output_edits["destinations_line"] = st.text_input(
            "Destinations line",
            value=output_edits.get("destinations_line", ""),
            key="edit_destinations_line",
        )

    days = list(grouped_days.keys())

    if days:
        day_tabs = st.tabs(days)

        for tab, day in zip(day_tabs, days):
            with tab:
                rows = grouped_days[day]
                day_edit = output_edits.setdefault("days", {}).setdefault(day, {})

                day_edit["title"] = st.text_input(
                    f"{day} title",
                    value=day_edit.get("title", create_day_title(rows)),
                    key=f"edit_{day}_title",
                )
                day_edit["city"] = st.text_input(
                    f"{day} city",
                    value=day_edit.get("city", get_primary_city(rows)),
                    key=f"edit_{day}_city",
                )
                day_edit["intro"] = st.text_area(
                    f"{day} intro",
                    value=day_edit.get("intro", create_day_intro(rows, detail_level=get_detail_level_name(output_edits))),
                    height=95,
                    key=f"edit_{day}_intro",
                )

                with st.expander(f"Edit {day} itinerary items", expanded=False):
                    for index, row in enumerate(rows, start=1):
                        row_id = row.get("row_id") or f"{day}_{index}"
                        row_edit = output_edits.setdefault("rows", {}).setdefault(row_id, {})
                        row_type = get_row_type(row)
                        item_label = row_edit.get("title") or row.get("title") or f"Item {index}"

                        with st.expander(f"{index}. {row_type}: {item_label}", expanded=False):
                            row_edit["title"] = st.text_input(
                                "Title / text",
                                value=row_edit.get("title", row.get("title", "")),
                                key=f"edit_{row_id}_title",
                            )
                            row_edit["city"] = st.text_input(
                                "City / location",
                                value=row_edit.get("city", row.get("city", "")),
                                key=f"edit_{row_id}_city",
                            )

                            if row_type == "Hotel":
                                row_edit["hotel_name"] = st.text_input(
                                    "Accommodation name",
                                    value=row_edit.get("hotel_name", row.get("hotel_name", "")),
                                    key=f"edit_{row_id}_hotel_name",
                                )
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    row_edit["hotel_nights"] = st.text_input(
                                        "Number of nights",
                                        value=row_edit.get("hotel_nights", row.get("hotel_nights", "")),
                                        key=f"edit_{row_id}_hotel_nights",
                                    )
                                    row_edit["room_category"] = st.text_input(
                                        "Room category",
                                        value=row_edit.get("room_category", row.get("room_category", "")),
                                        key=f"edit_{row_id}_room",
                                    )
                                with col_b:
                                    row_edit["meal_plan"] = st.text_input(
                                        "Meal plan",
                                        value=row_edit.get("meal_plan", row.get("meal_plan", "")),
                                        key=f"edit_{row_id}_meal",
                                    )
                            else:
                                col1, col2 = st.columns(2)
                                with col1:
                                    row_edit["time"] = st.text_input(
                                        "Time",
                                        value=row_edit.get("time", row.get("time", "")),
                                        key=f"edit_{row_id}_time",
                                    )
                                    row_edit["meeting_point"] = st.text_input(
                                        "Meeting point",
                                        value=row_edit.get("meeting_point", row.get("meeting_point", "")),
                                        key=f"edit_{row_id}_meeting",
                                    )
                                    row_edit["duration"] = st.text_input(
                                        "Duration",
                                        value=row_edit.get("duration", row.get("duration", "")),
                                        key=f"edit_{row_id}_duration",
                                    )
                                with col2:
                                    row_edit["end_point"] = st.text_input(
                                        "End point",
                                        value=row_edit.get("end_point", row.get("end_point", "")),
                                        key=f"edit_{row_id}_end",
                                    )
                                    row_edit["luggage_included"] = st.text_input(
                                        "Luggage included",
                                        value=row_edit.get("luggage_included", row.get("luggage_included", "")),
                                        key=f"edit_{row_id}_luggage",
                                    )

                                row_edit["notable_sights_text"] = st.text_area(
                                    "Notable sights, one per line",
                                    value=row_edit.get("notable_sights_text", list_to_text(row.get("notable_sights", []))),
                                    height=90,
                                    key=f"edit_{row_id}_sights",
                                )
                                row_edit["client_description"] = st.text_area(
                                    "Short description / note",
                                    value=row_edit.get("client_description", row.get("client_description") or get_activity_description(row, get_detail_level_name(output_edits))),
                                    height=75,
                                    key=f"edit_{row_id}_description",
                                )
                                row_edit["includes_text"] = st.text_area(
                                    "Inclusions, one per line",
                                    value=row_edit.get("includes_text", list_to_text(row.get("includes", []))),
                                    height=100,
                                    key=f"edit_{row_id}_includes",
                                )

    with st.expander("Edit final inclusion / exclusion pages", expanded=False):
        output_edits["whats_included_text"] = st.text_area(
            "What’s included, one item per line",
            value=output_edits.get("whats_included_text", ""),
            height=220,
            key="edit_whats_included_text",
        )
        output_edits["whats_not_included_text"] = st.text_area(
            "What’s not included, one item per line",
            value=output_edits.get("whats_not_included_text", ""),
            height=180,
            key="edit_whats_not_included_text",
        )


def build_itinerary_html(parsed_rows, grouped_days, output_edits=None):
    output_edits = output_edits or {}
    preset_name = get_color_preset_name(output_edits)
    colors = get_color_preset(output_edits)
    colors_json = esc(json.dumps(colors))

    trip_title = output_edits.get("trip_title") or create_trip_title(parsed_rows, grouped_days)
    trip_subtitle = output_edits.get("trip_subtitle") or create_trip_subtitle(parsed_rows, grouped_days)
    destinations_line = output_edits.get("destinations_line") or create_destinations_line(parsed_rows)
    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    journey_arc = create_journey_arc(grouped_days)

    if output_edits.get("whats_included_text"):
        whats_included = text_to_list(output_edits.get("whats_included_text"))
    else:
        whats_included = create_whats_included(parsed_rows, grouped_days)

    optional_addons = create_optional_addons(parsed_rows)
    activity_inclusions = create_activity_inclusions(parsed_rows)

    if output_edits.get("whats_not_included_text"):
        whats_not_included = text_to_list(output_edits.get("whats_not_included_text"))
    else:
        whats_not_included = create_whats_not_included()

    html_text = f"""
    <style>
        .preview-background {{
            --page-bg: {esc(colors['page_bg'])};
            --preview-bg: {esc(colors['preview_bg'])};
            --ink: {esc(colors['ink'])};
            --body: {esc(colors['body'])};
            --muted: {esc(colors['muted'])};
            --line: {esc(colors['line'])};
            --card: {esc(colors['card'])};
            --accent: {esc(colors['accent'])};
            background: var(--preview-bg);
            padding: 32px 0 60px 0;
        }}

        .a4-page {{
            width: 794px;
            min-height: 1123px;
            background: var(--page-bg);
            color: var(--ink);
            margin: 0 auto 32px auto;
            padding: 66px 64px;
            box-sizing: border-box;
            font-family: Georgia, 'Times New Roman', serif;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
            break-after: page;
            page-break-after: always;
            overflow: hidden;
        }}

        .cover-page {{
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}

        .cover-kicker {{
            font-family: Arial, sans-serif;
            font-size: 13px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 18px;
        }}

        .cover-title {{
            font-size: 54px;
            line-height: 1.05;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 18px;
        }}

        .cover-subtitle {{
            font-size: 24px;
            line-height: 1.25;
            color: var(--ink);
            margin-bottom: 18px;
        }}

        .cover-destinations {{
            font-family: Arial, sans-serif;
            font-size: 15px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--body);
            margin-top: 24px;
        }}

        .glance-card,
        .journey-arc {{
            background: var(--card);
            border: 1px solid var(--line);
            padding: 28px;
        }}

        .glance-card {{
            margin-bottom: 34px;
        }}

        .glance-title,
        .journey-title {{
            font-size: 30px;
            margin-bottom: 16px;
            color: var(--ink);
        }}

        .glance-row {{
            display: grid;
            grid-template-columns: 165px 1fr;
            gap: 18px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.45;
            padding: 8px 0;
            border-bottom: 1px solid var(--line);
        }}

        .glance-label {{
            font-weight: 700;
            color: var(--ink);
        }}

        .glance-value {{
            color: var(--body);
        }}

        .journey-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: var(--body);
        }}

        .journey-table th {{
            text-align: left;
            color: var(--ink);
            font-weight: 700;
            padding: 10px 8px;
            border-bottom: 1px solid var(--line);
        }}

        .journey-table td {{
            padding: 12px 8px;
            vertical-align: top;
            border-bottom: 1px solid var(--line);
            line-height: 1.45;
        }}

        .journey-days {{
            white-space: nowrap;
        }}

        .day-label {{
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 6px;
            color: var(--ink);
        }}

        .day-title {{
            font-size: 27px;
            font-weight: 500;
            margin-bottom: 12px;
            color: var(--ink);
        }}

        .city {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 20px;
        }}

        .intro {{
            font-size: 15px;
            line-height: 1.5;
            margin-bottom: 22px;
            color: var(--body);
        }}

        .content-block {{
            margin-bottom: 15px;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .section-title {{
            font-family: Arial, sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-top: 15px;
            margin-bottom: 5px;
            color: var(--accent);
        }}

        .small-section {{
            margin-top: 10px;
        }}

        .body-text {{
            font-size: 13.5px;
            line-height: 1.38;
            color: var(--body);
            margin-bottom: 5px;
        }}

        .strong-line {{
            font-weight: 600;
        }}

        .meta-label {{
            font-family: Arial, sans-serif;
            font-weight: 700;
            font-size: 12px;
            color: var(--ink);
        }}

        .final-page-title {{
            font-size: 34px;
            margin-bottom: 22px;
            color: var(--ink);
        }}

        .activity-inclusion-block {{
            margin-bottom: 18px;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .activity-inclusion-title {{
            font-size: 18px;
            line-height: 1.25;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 6px;
        }}

        ul {{
            margin-top: 5px;
            margin-bottom: 13px;
            padding-left: 21px;
        }}

        li {{
            font-size: 13.5px;
            line-height: 1.36;
            margin-bottom: 3px;
            color: var(--body);
        }}

        .final-list li {{
            margin-bottom: 5px;
        }}

        @media print {{
            @page {{
                size: A4 portrait;
                margin: 0;
            }}

            .preview-background {{
                background: white;
                padding: 0;
            }}

            .a4-page {{
                width: 210mm;
                height: 297mm;
                min-height: 297mm;
                margin: 0;
                box-shadow: none;
                break-after: page;
                page-break-after: always;
            }}
        }}
    </style>

    <div class="preview-background" data-preset="{esc(preset_name)}" data-colors="{colors_json}">

        <div class="a4-page cover-page">
            <div class="cover-kicker">Curated Travel Itinerary</div>
            <div class="cover-title">{esc(trip_title)}</div>
            <div class="cover-subtitle">{esc(trip_subtitle)}</div>
            <div class="cover-destinations">{esc(destinations_line)}</div>
        </div>

        <div class="a4-page">
            <div class="glance-card">
                <div class="glance-title">Your Trip at a Glance</div>
    """

    for label, value in trip_glance.items():
        html_text += f"""
                <div class="glance-row">
                    <div class="glance-label">{esc(label)}</div>
                    <div class="glance-value">{esc(value)}</div>
                </div>
        """

    html_text += """
            </div>

            <div class="journey-arc">
                <div class="journey-title">Your Journey Arc</div>
                <table class="journey-table">
                    <thead>
                        <tr>
                            <th>Chapter</th>
                            <th>Days</th>
                            <th>What You’ll Experience</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for chapter in journey_arc:
        html_text += f"""
                        <tr>
                            <td>{esc(chapter["chapter"])}</td>
                            <td class="journey-days">{esc(chapter["days"])}</td>
                            <td>{esc(chapter["experience"])}</td>
                        </tr>
        """

    html_text += """
                    </tbody>
                </table>
            </div>
        </div>
    """

    for day, rows in grouped_days.items():
        html_text += render_day_pages(day, rows, output_edits)

    html_text += render_split_list_pages("What’s included", whats_included)
    html_text += render_optional_addons_pages(optional_addons)
    html_text += render_activity_inclusions_pages(activity_inclusions)
    html_text += render_split_list_pages("What’s not included", whats_not_included)

    html_text += "</div>"

    return html_text


def build_full_html_document(itinerary_html):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Itinerary Preview</title>
</head>
<body style="margin: 0;">
{itinerary_html}
</body>
</html>
"""


def save_html_file(itinerary_html):
    try:
        outputs_folder = Path("outputs")
        outputs_folder.mkdir(exist_ok=True)

        output_path = outputs_folder / "itinerary_preview.html"
        full_html = build_full_html_document(itinerary_html)
        output_path.write_text(full_html, encoding="utf-8")

        return output_path
    except Exception as error:
        st.error("Could not save the HTML file to disk. The preview still works, but HTML/PDF downloads may not work.")
        with st.expander("HTML save error details"):
            st.exception(error)
        return None


def save_pdf_file(html_path):
    try:
        if not html_path:
            raise ValueError("HTML path is missing. Regenerate the itinerary before creating the PDF.")

        outputs_folder = Path("outputs")
        outputs_folder.mkdir(exist_ok=True)

        pdf_path = outputs_folder / "itinerary_preview.pdf"
        export_html_to_pdf(html_path, pdf_path)

        return pdf_path
    except Exception as error:
        st.error("Could not save the PDF file to disk.")
        with st.expander("PDF save error details"):
            st.exception(error)
        return None



def get_current_itinerary_state():
    """Return edited rows/grouped days for the current session state."""
    parsed_rows = st.session_state.get("parsed_rows", [])
    output_edits = st.session_state.get("output_edits", {})

    if not parsed_rows:
        return [], {}

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    return edited_rows, group_rows_by_day(edited_rows)


def get_itinerary_stats(parsed_rows=None, grouped_days=None):
    parsed_rows = parsed_rows if parsed_rows is not None else st.session_state.get("parsed_rows", [])
    grouped_days = grouped_days if grouped_days is not None else group_rows_by_day(parsed_rows)

    destinations = []
    for row in parsed_rows:
        city = str(row.get("city", "")).strip()
        if city and city not in destinations:
            destinations.append(city)

    activities = [row for row in parsed_rows if get_row_type(row) == "Activity" and not row.get("is_optional")]
    optional_rows = [row for row in parsed_rows if row.get("is_optional")]
    hotels = [row for row in parsed_rows if get_row_type(row) == "Hotel"]
    self_arranged = [row for row in parsed_rows if get_row_type(row) in TRANSPORT_TYPES and is_self_arranged(row)]

    return {
        "days": len(grouped_days),
        "destinations": len(destinations),
        "destination_names": destinations,
        "activities": len(activities),
        "hotels": len(hotels),
        "self_arranged": len(self_arranged),
        "optional_rows": len(optional_rows),
    }


def render_parser_diagnostics_panel():
    warnings = st.session_state.get("parser_diagnostics", [])
    if not warnings:
        return

    with st.expander(f"Parser diagnostics ({len(warnings)} notice(s))", expanded=False):
        st.caption(
            "These are things the parser could not fully understand. "
            "If something looks wrong in the output, the cause may be listed here."
        )
        for entry in warnings:
            st.markdown(f"**{entry['category']}** — {entry['message']}")
            if entry.get("raw"):
                st.code(entry["raw"], language=None)

        diagnostics_text = []
        for entry in warnings:
            diagnostics_text.append(f"[{entry['category']}] {entry['message']}")
            if entry.get("raw"):
                diagnostics_text.append(f"  Raw: {entry['raw']}")
        with st.expander("Show diagnostics text for copying"):
            st.code("\n".join(diagnostics_text), language=None)


def make_title_suggestions(parsed_rows, grouped_days):
    cities = []
    for row in parsed_rows:
        city = str(row.get("city", "")).strip()
        if city and city not in cities:
            cities.append(city)

    full_text = " ".join(str(row.get("details", "")) for row in parsed_rows).lower()
    suggestions = []

    if any(marker in full_text for marker in ["northern light", "aurora", "lapland", "arctic"]):
        suggestions.extend(["Nordic Winter Journey", "Arctic Lights Journey", "Lapland & Nordic Lights Escape"])

    if "fjord" in full_text or "norway in a nutshell" in full_text:
        suggestions.extend(["Nordic Fjord Journey", "Fjords & Capitals Discovery", "Scenic Nordic Journey"])

    if len(cities) >= 4:
        suggestions.append("Grand Nordic Journey")

    if len(cities) == 2:
        suggestions.append(f"{cities[0]} & {cities[1]} Journey")

    if not suggestions:
        suggestions.extend(["Nordic Discovery Journey", "Curated Nordic Escape", "Scandinavian City & Nature Journey"])

    clean = []
    for suggestion in suggestions:
        if suggestion not in clean:
            clean.append(suggestion)
    return clean[:6]


def get_activity_sections_count(parsed_rows):
    return len(create_activity_inclusions(parsed_rows))


def build_review_items(parsed_rows=None, grouped_days=None):
    """Return practical client-facing review items for the sidebar.

    These are not technical parser diagnostics. They are consultant-friendly
    checks that help decide whether an itinerary should be reviewed before export.
    """

    parsed_rows = parsed_rows if parsed_rows is not None else st.session_state.get("parsed_rows", [])
    grouped_days = grouped_days if grouped_days is not None else group_rows_by_day(parsed_rows)
    items = []

    def add_item(severity, message):
        entry = {"severity": severity, "message": message}
        if entry not in items:
            items.append(entry)

    activities = [row for row in parsed_rows if get_row_type(row) == "Activity" and not row.get("is_optional")]
    hotels = [row for row in parsed_rows if get_row_type(row) == "Hotel" and not row.get("is_optional")]
    optional_rows = [row for row in parsed_rows if row.get("is_optional")]
    self_arranged = [row for row in parsed_rows if get_row_type(row) in TRANSPORT_TYPES and is_self_arranged(row) and not row.get("is_optional")]

    for row in activities:
        title = create_client_activity_title(row) or row.get("title", "Activity")
        text = f'{title} {row.get("details", "")}'.lower()
        day = row.get("day", "")
        meeting_label, meeting_point = get_activity_logistics(row)

        is_simple_ticket = any(marker in text for marker in ["hop-on", "hop on", "ticket", "fløibanen", "floibanen", "fjellheisen"])
        if not meeting_point and not is_simple_ticket:
            add_item("warning", f"{day}: activity may need a meeting point — {title}")
        if not row.get("duration") and not is_simple_ticket:
            add_item("info", f"{day}: activity has no duration — {title}")

    for row in hotels:
        day = row.get("day", "")
        name = row.get("hotel_name") or row.get("title") or "Accommodation"
        if not row.get("hotel_nights"):
            add_item("warning", f"{day}: accommodation missing number of nights — {name}")
        if not row.get("room_category"):
            add_item("info", f"{day}: accommodation missing room category — {name}")
        if not row.get("meal_plan"):
            add_item("info", f"{day}: accommodation missing meal plan — {name}")
        elif "without breakfast" in str(row.get("meal_plan", "")).lower():
            add_item("info", f"{day}: accommodation is marked without breakfast — {name}")

    for row in self_arranged:
        title = row.get("title", "Self-arranged travel")
        add_item("warning", f"{row.get('day', '')}: self-arranged travel shown — {title}")

    if optional_rows:
        add_item("info", f"Optional add-ons detected: {len(optional_rows)} item(s)")

    for day, rows in grouped_days.items():
        activity_count = sum(1 for row in rows if get_row_type(row) == "Activity")
        block_count = len(rows)
        if block_count >= 7 or activity_count >= 3:
            add_item("warning", f"{day}: busy day — review page balance before export")

    if activities and get_activity_sections_count(parsed_rows) < len(activities):
        add_item("warning", "Some activities may be missing from Activity inclusions")

    return items


def get_itinerary_health(review_items):
    warnings = sum(1 for item in review_items if item.get("severity") == "warning")
    if warnings == 0 and len(review_items) <= 1:
        return "Excellent"
    if warnings <= 2:
        return "Good"
    return "Needs review"


def render_sidebar_review_assistant(parsed_rows, grouped_days, stats):
    review_items = build_review_items(parsed_rows, grouped_days)
    health = get_itinerary_health(review_items)

    st.subheader("Itinerary health")
    if health == "Excellent":
        st.success("Excellent")
    elif health == "Good":
        st.info("Good")
    else:
        st.warning("Needs review")

    st.subheader("Issues to review")
    if review_items:
        for item in review_items[:8]:
            icon = "⚠" if item.get("severity") == "warning" else "•"
            st.caption(f"{icon} {item['message']}")
        if len(review_items) > 8:
            st.caption(f"+ {len(review_items) - 8} more item(s) in the editable itinerary.")
    else:
        st.caption("No practical review issues detected.")

    st.subheader("Ready to export")
    checklist = [
        (stats["days"] > 0, "Days detected"),
        (stats["destinations"] > 0, "Destinations detected"),
        (stats["hotels"] > 0, "Accommodation detected"),
        (stats["activities"] == 0 or get_activity_sections_count(parsed_rows) >= stats["activities"], "Activity inclusions ready"),
        (st.session_state.get("pdf_status") == "Ready", "PDF created"),
    ]
    for ok, label in checklist:
        icon = "✓" if ok else "⚠"
        st.caption(f"{icon} {label}")

def render_sidebar_snapshot():
    parsed_rows = st.session_state.get("parsed_rows", [])
    if not parsed_rows:
        st.caption("Generate an itinerary to see stats, quality checks, and creative tools here.")
        return

    edited_rows, grouped_days = get_current_itinerary_state()
    stats = get_itinerary_stats(edited_rows, grouped_days)
    diagnostics_count = len(st.session_state.get("parser_diagnostics", []))

    st.divider()
    st.subheader("Snapshot")
    stat_a, stat_b = st.columns(2)
    stat_a.metric("Days", stats["days"])
    stat_b.metric("Places", stats["destinations"])
    stat_c, stat_d = st.columns(2)
    stat_c.metric("Activities", stats["activities"])
    stat_d.metric("Hotels", stats["hotels"])

    if stats["self_arranged"]:
        st.markdown(f'<div class="sidebar-pill">Self-arranged travel: {stats["self_arranged"]}</div>', unsafe_allow_html=True)
    if stats["optional_rows"]:
        st.markdown(f'<div class="sidebar-pill">Optional add-ons: {stats["optional_rows"]}</div>', unsafe_allow_html=True)

    render_sidebar_review_assistant(edited_rows, grouped_days, stats)
    st.caption(f"PDF status: {st.session_state.get('pdf_status', 'Not created')}")

    st.subheader("Creative tools")
    suggestions = make_title_suggestions(edited_rows, grouped_days)
    if suggestions:
        index = st.session_state.get("title_suggestion_index", 0) % len(suggestions)
        suggestion = suggestions[index]
        st.caption(f"Title idea: {suggestion}")
        if st.button("Use title idea", use_container_width=True):
            st.session_state.output_edits["trip_title"] = suggestion
            st.session_state.title_suggestion_index = index + 1
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Needs refresh"
            st.rerun()
        if st.button("Try another title", use_container_width=True):
            st.session_state.title_suggestion_index = index + 1
            st.rerun()


def initialise_state():
    defaults = {
        "itinerary_html": "",
        "html_path": None,
        "pdf_bytes": None,
        "parsed_rows": [],
        "output_edits": {},
        "last_generated_raw_text": "",
        "parser_diagnostics": [],
        "pdf_status": "Not created",
        "detail_level": "Standard client itinerary",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_project_json(uploaded_file):
    try:
        data = json.loads(uploaded_file.read().decode("utf-8"))
        raw_text = data.get("raw_text", "")
        output_edits = data.get("output_edits", {})

        parsed_rows = parse_itinerary(raw_text)
        grouped_days = group_rows_by_day(parsed_rows)

        st.session_state.parsed_rows = parsed_rows
        st.session_state.output_edits = output_edits or make_output_edit_state(parsed_rows, grouped_days)
        st.session_state.detail_level = st.session_state.output_edits.get("detail_level", st.session_state.get("detail_level", "Standard client itinerary"))
        st.session_state.last_generated_raw_text = raw_text
        st.session_state.pdf_bytes = None

        edited_rows = apply_output_edits(parsed_rows, st.session_state.output_edits)
        edited_grouped_days = group_rows_by_day(edited_rows)
        st.session_state.itinerary_html = build_itinerary_html(edited_rows, edited_grouped_days, st.session_state.output_edits)
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
        st.session_state.raw_text_input = raw_text

        st.success("Editable project loaded.")
    except Exception as error:
        st.error("The project JSON could not be loaded.")
        st.exception(error)



initialise_state()

with st.sidebar:
    st.subheader("Settings")
    current_preset = st.session_state.get("color_preset", "Classic Agent")
    if current_preset not in PRESET_ORDER:
        current_preset = "Classic Agent"

    selected_preset = st.selectbox(
        "Color preset",
        PRESET_ORDER,
        index=PRESET_ORDER.index(current_preset),
        help="Classic Agent keeps the neutral travel-agent look. Booknordics B2C uses a cleaner branded palette.",
    )
    st.session_state.color_preset = selected_preset

    if selected_preset == "Classic Agent":
        st.caption("Warm, neutral, B2B-friendly.")
    else:
        st.caption("Clean, bright, B2C-friendly.")

    current_detail = st.session_state.get("detail_level", "Standard client itinerary")
    if current_detail not in DETAIL_LEVELS:
        current_detail = "Standard client itinerary"

    selected_detail = st.selectbox(
        "Detail level",
        DETAIL_LEVELS,
        index=DETAIL_LEVELS.index(current_detail),
        help="Controls how much client-facing description is generated. Existing manual edits are preserved.",
    )
    st.session_state.detail_level = selected_detail
    if selected_detail == "Elegant concise":
        st.caption("Short, polished, and practical.")
    elif selected_detail == "Rich descriptive":
        st.caption("Warmer and more atmospheric.")
    else:
        st.caption("Balanced detail for most client itineraries.")

    if st.session_state.get("output_edits"):
        st.session_state.output_edits["color_preset"] = selected_preset
        st.session_state.output_edits["detail_level"] = selected_detail

    show_debug = st.checkbox("Show parser/debug panels", value=False)

    st.divider()
    st.subheader("Project")
    uploaded_project = st.file_uploader("Load editable project JSON", type=["json"])

    if uploaded_project is not None and st.button("Load project", use_container_width=True):
        load_project_json(uploaded_project)
        st.rerun()

    render_sidebar_snapshot()

st.markdown(
    f"""
    <div class="app-hero">
        <h1>Itinerary Creator</h1>
        <p>Paste itinerary rows, review the generated output, then export a polished A4 itinerary.</p>
        <p style="font-size: 0.85rem; opacity: 0.65; margin-top: 0.4rem;">Version: {APP_VERSION}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Step 1 — Paste raw itinerary text", expanded=not bool(st.session_state.itinerary_html)):
    st.markdown('<div class="workflow-note">Paste the full itinerary table or copied Excel rows here.</div>', unsafe_allow_html=True)
    raw_text = st.text_area(
        "Raw Excel text",
        height=300,
        placeholder="Paste itinerary rows here...",
        key="raw_text_input",
    )

    if st.button("Generate itinerary", type="primary", use_container_width=True):
        if raw_text.strip():
            diagnostics.reset()
            parsed_rows = parse_itinerary(raw_text)
            grouped_days = group_rows_by_day(parsed_rows)
            duplicate_count = get_duplicate_count(raw_text, parsed_rows)

            st.session_state.parsed_rows = parsed_rows
            st.session_state.output_edits = make_output_edit_state(parsed_rows, grouped_days)
            st.session_state.last_generated_raw_text = raw_text
            st.session_state.pdf_bytes = None
            st.session_state.pdf_status = "Not created"
            st.session_state.parser_diagnostics = diagnostics.get_warnings()

            edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
            edited_grouped_days = group_rows_by_day(edited_rows)
            st.session_state.itinerary_html = build_itinerary_html(
                edited_rows,
                edited_grouped_days,
                st.session_state.output_edits,
            )
            st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

            st.success(f"Parsed {len(parsed_rows)} itinerary rows across {len(grouped_days)} days.")

            if duplicate_count:
                st.warning(f"Skipped approximately {duplicate_count} duplicate, continuation, or malformed row(s).")

            overflow_warnings = get_overflow_warnings(edited_grouped_days)
            for warning in overflow_warnings:
                st.warning(warning)

            if st.session_state.html_path:
                st.success("HTML preview prepared.")

        else:
            st.warning("Please paste some itinerary text first.")

if show_debug:
    render_parser_diagnostics_panel()

if show_debug and st.session_state.parsed_rows:
    with st.expander("Debug tools", expanded=False):
        st.dataframe(st.session_state.parsed_rows, use_container_width=True)
        st.write("Day grouping")
        for day, rows in group_rows_by_day(st.session_state.parsed_rows).items():
            st.write(f"{day}: {len(rows)} rows")
            for row in rows:
                st.write(
                    f"- {row.get('type')} / {row.get('effective_type')}: "
                    f"{row.get('title')} ({row.get('city')})"
                )

if st.session_state.itinerary_html:
    with st.expander("Step 2 — Preview itinerary", expanded=False):
        st.html(st.session_state.itinerary_html)

if st.session_state.parsed_rows and st.session_state.output_edits:
    with st.expander("Step 3 — Review & edit generated itinerary", expanded=False):
        render_output_editor(
            st.session_state.parsed_rows,
            group_rows_by_day(apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)),
            st.session_state.output_edits,
        )

    edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    rebuilt_html = build_itinerary_html(
        edited_rows,
        edited_grouped_days,
        st.session_state.output_edits,
    )

    if rebuilt_html != st.session_state.itinerary_html:
        st.session_state.pdf_bytes = None
        if st.session_state.itinerary_html:
            st.session_state.pdf_status = "Needs refresh"

    st.session_state.itinerary_html = rebuilt_html
    st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

if st.session_state.itinerary_html:
    st.subheader("Step 4 — Export")
    st.markdown('<div class="workflow-note">Save your editable project, download the HTML preview, or create a PDF.</div>', unsafe_allow_html=True)

    html_path = Path(st.session_state.html_path) if st.session_state.html_path else None
    project_data = {
        "app_version": APP_VERSION,
        "raw_text": st.session_state.get("last_generated_raw_text", ""),
        "output_edits": st.session_state.get("output_edits", {}),
    }

    export_col_1, export_col_2, export_col_3, export_col_4 = st.columns(4)

    with export_col_1:
        st.download_button(
            "Download project JSON",
            data=json.dumps(project_data, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="itinerary_project.json",
            mime="application/json",
            use_container_width=True,
        )

    with export_col_2:
        if html_path and html_path.exists():
            with open(html_path, "rb") as html_file:
                st.download_button(
                    label="Download HTML",
                    data=html_file,
                    file_name="itinerary_preview.html",
                    mime="text/html",
                    use_container_width=True,
                )
        else:
            st.button("Download HTML", disabled=True, use_container_width=True)
            st.caption("HTML file not available.")

    with export_col_3:
        if st.button("Create PDF", use_container_width=True):
            try:
                with st.spinner("Creating PDF..."):
                    pdf_path = save_pdf_file(html_path)
                    if pdf_path is None:
                        st.session_state.pdf_bytes = None
                        st.session_state.pdf_status = "PDF failed"
                    else:
                        st.session_state.pdf_bytes = Path(pdf_path).read_bytes()
                        st.session_state.pdf_status = "Ready"

                if st.session_state.pdf_bytes:
                    st.success("PDF created. Use the download button.")

            except Exception as error:
                st.session_state.pdf_status = "PDF failed"
                st.error(
                    "PDF export failed in this environment. The itinerary preview and HTML download still work."
                )
                with st.expander("PDF export error details"):
                    st.exception(error)

    with export_col_4:
        if st.session_state.pdf_bytes:
            st.download_button(
                label="Download PDF",
                data=st.session_state.pdf_bytes,
                file_name="itinerary_preview.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("Download PDF", disabled=True, use_container_width=True)
            st.caption(st.session_state.get("pdf_status", "Not created"))
