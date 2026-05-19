from pathlib import Path
import base64
import copy
from datetime import datetime, timezone
import html
import json
import re

import streamlit as st
import streamlit.components.v1 as components

from parser import parse_itinerary
from pdf_exporter import export_html_to_pdf
from generator import (
    TRANSPORT_TYPES,
    create_day_intro,
    create_day_title,
    create_destinations_line,
    create_journey_arc,
    create_trip_glance,
    create_trip_subtitle,
    create_trip_title,
    create_whats_included,
    create_whats_not_included,
    get_primary_city,
    get_row_type,
    group_rows_by_day,
)


APP_VERSION = "2026-05-19 v17 project-save-polish"
PROJECT_SCHEMA_VERSION = 1


st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide",
)

st.title("Itinerary Creator")
st.caption(f"Fix version: {APP_VERSION}")

st.write(
    "Paste raw Excel itinerary text below. "
    "The app will turn it into a polished A4 itinerary preview."
)

if "raw_text_input" not in st.session_state:
    st.session_state.raw_text_input = ""


def queue_project_load():
    uploaded_file = st.session_state.get("project_upload_file")

    if uploaded_file is None:
        st.session_state.project_load_error = "Please choose a project JSON file first."
        return

    try:
        project_data = json.loads(uploaded_file.getvalue().decode("utf-8"))
    except Exception as error:
        st.session_state.project_load_error = f"Could not read the project file: {error}"
        return

    if not isinstance(project_data, dict):
        st.session_state.project_load_error = "The project file is not valid."
        return

    raw_project_text = str(project_data.get("raw_text", "")).strip()

    if not raw_project_text:
        st.session_state.project_load_error = "The project file does not contain raw itinerary text."
        return

    st.session_state.pending_project_data = project_data
    st.session_state.raw_text_input = raw_project_text
    st.session_state.project_load_error = ""


with st.sidebar:
    st.header("Project")
    st.file_uploader(
        "Load editable project JSON",
        type=["json"],
        key="project_upload_file",
        help="Load a project you previously downloaded from this app.",
    )
    st.button("Load project", on_click=queue_project_load, use_container_width=True)

    if st.session_state.get("project_load_error"):
        st.error(st.session_state.project_load_error)

raw_text = st.text_area(
    "Raw Excel text",
    height=300,
    placeholder="Paste itinerary rows here...",
    key="raw_text_input",
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
        return "Featured experience"

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


def build_activity_block(row):
    """
    Keep the day-by-day section clean.
    Activity inclusions are shown later on the separate Activity inclusions page.
    """

    title = row.get("title", "")
    time = row.get("time", "")
    meeting_point = row.get("meeting_point", "")
    end_point = row.get("end_point", "")
    notable_sights = normalize_list(row.get("notable_sights", []))

    html_text = f'<div class="content-block activity-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += f'<div class="section-title">{esc(get_time_period(time))}</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if time:
        html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(time)}</div>'

    if meeting_point:
        html_text += f'<div class="body-text"><span class="meta-label">Meeting point:</span> {esc(meeting_point)}</div>'

    if end_point:
        html_text += f'<div class="body-text"><span class="meta-label">End point:</span> {esc(end_point)}</div>'

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
    includes = normalize_list(row.get("includes", []))
    luggage_included = row.get("luggage_included", "")

    html_text = f'<div class="content-block transport-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Travel today</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if time:
        html_text += f'<div class="body-text"><span class="meta-label">Time:</span> {esc(time)}</div>'

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



def is_self_transfer(row):
    """Detect self-guided transfers so they are not treated as included services."""

    row_type = get_row_type(row)
    text = f'{row.get("title", "")} {row.get("details", "")}'.lower()

    return row_type == "Transfer" and "self transfer" in text


def build_self_transfer_block(row):
    title = row.get("title", "")
    city = row.get("city", "")

    html_text = f'<div class="content-block self-transfer-block" data-row-id="{esc(row.get("row_id", ""))}">'
    html_text += '<div class="section-title">Self-guided transfer</div>'
    html_text += f'<div class="body-text strong-line">{esc(title)}</div>'

    if city:
        html_text += f'<div class="body-text"><span class="meta-label">Location:</span> {esc(city)}</div>'

    html_text += (
        '<div class="body-text muted-note">'
        'This is a self-guided transfer, so please make your own way between these points. '
        'Transport costs are not included unless specifically stated elsewhere in the itinerary.'
        '</div>'
    )
    html_text += "</div>"

    return {
        "kind": "self_transfer",
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

    for row in rows:
        row_type = get_row_type(row)
        title = row.get("title", "")

        if row_type == "Transfer" and is_self_transfer(row):
            blocks.append(build_self_transfer_block(row))

        elif row_type == "Departure":
            blocks.append(build_departure_block(row))

        elif row_type in ["Arrival", "Hotel"]:
            if title:
                included_items.append(title)

        elif row_type == "Transfer":
            if title:
                included_items.append(title)

        elif row_type in TRANSPORT_TYPES:
            blocks.append(build_transport_block(row))

        elif row_type == "Activity":
            blocks.append(build_activity_block(row))

        elif row_type == "Leisure":
            blocks.append(build_leisure_block(row))

        elif title:
            included_items.append(title)

    included_block = build_included_today_block(included_items)

    if included_block:
        blocks.append(included_block)

    return blocks


def render_day_pages(day, rows, output_edits=None):
    """
    One itinerary day renders as one A4 page.
    This deliberately avoids the earlier manual page splitter, which caused
    day-boundary bleed/duplication.
    """

    day_edits = (output_edits or {}).get("days", {}).get(day, {})
    day_title = day_edits.get("title") or create_day_title(rows)
    day_intro = day_edits.get("intro") or create_day_intro(rows)
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


def create_activity_inclusions(parsed_rows):
    activity_sections = []

    for row in parsed_rows:
        if get_row_type(row) != "Activity":
            continue

        title = row.get("title", "").strip()
        includes = normalize_list(row.get("includes", []))

        if not title or not includes:
            continue

        activity_sections.append({
            "title": title,
            "includes": includes,
        })

    return activity_sections


def render_activity_inclusions_pages(activity_sections, sections_per_page=5):
    if not activity_sections:
        return ""

    html_text = ""

    for start in range(0, len(activity_sections), sections_per_page):
        chunk = activity_sections[start:start + sections_per_page]
        continued = "" if start == 0 else " continued"

        html_text += f"""
        <div class="a4-page final-list-page activity-inclusions-page">
            <div class="final-page-title">Activity inclusions{continued}</div>
        """

        for section in chunk:
            html_text += '<div class="activity-inclusion-block">'
            html_text += f'<div class="activity-inclusion-title">{esc(section["title"])}</div>'
            html_text += render_list_items(section["includes"], class_name="final-list")
            html_text += "</div>"

        html_text += "</div>"

    return html_text


def auto_download_file(file_bytes, file_name, mime_type):
    """
    Triggers a browser download after a Streamlit button click.
    The normal Streamlit download button below remains as a fallback.
    """

    encoded = base64.b64encode(file_bytes).decode("utf-8")
    safe_file_name = json.dumps(file_name)
    safe_mime_type = json.dumps(mime_type)

    components.html(
        f"""
        <script>
        const base64Data = "{encoded}";
        const fileName = {safe_file_name};
        const mimeType = {safe_mime_type};

        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);

        for (let i = 0; i < byteCharacters.length; i++) {{
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }}

        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], {{ type: mimeType }});
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setTimeout(() => URL.revokeObjectURL(url), 1000);
        </script>
        """,
        height=0,
    )




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


def make_output_edit_state(parsed_rows, grouped_days):
    """
    Creates editable values from the generated output.
    The raw Excel input stays untouched; these fields control the preview/export.
    """

    edits = {
        "trip_title": create_trip_title(parsed_rows, grouped_days),
        "trip_subtitle": create_trip_subtitle(parsed_rows, grouped_days),
        "destinations_line": create_destinations_line(parsed_rows),
        "days": {},
        "rows": {},
        "whats_included_text": list_to_text(create_whats_included(parsed_rows, grouped_days)),
        "whats_not_included_text": list_to_text(create_whats_not_included(parsed_rows)),
    }

    for day, rows in grouped_days.items():
        edits["days"][day] = {
            "title": create_day_title(rows),
            "intro": create_day_intro(rows),
            "city": get_primary_city(rows),
        }

        for row in rows:
            row_id = row.get("row_id") or f'line_{row.get("line_number", len(edits["rows"]))}'
            edits["rows"][row_id] = {
                "title": row.get("title", ""),
                "city": row.get("city", ""),
                "time": row.get("time", ""),
                "meeting_point": row.get("meeting_point", ""),
                "end_point": row.get("end_point", ""),
                "luggage_included": row.get("luggage_included", ""),
                "notable_sights_text": list_to_text(row.get("notable_sights", [])),
                "includes_text": list_to_text(row.get("includes", [])),
            }

    return edits


def apply_output_edits(parsed_rows, output_edits):
    """
    Applies edited output values to a copy of parsed rows.
    """

    edited_rows = copy.deepcopy(parsed_rows)
    row_edits = (output_edits or {}).get("rows", {})

    for row in edited_rows:
        row_id = row.get("row_id") or f'line_{row.get("line_number", "")}'
        edits = row_edits.get(row_id, {})

        for key in ["title", "city", "time", "meeting_point", "end_point", "luggage_included"]:
            if key in edits:
                row[key] = edits.get(key, "")

        if "notable_sights_text" in edits:
            row["notable_sights"] = text_to_list(edits.get("notable_sights_text", ""))

        if "includes_text" in edits:
            row["includes"] = text_to_list(edits.get("includes_text", ""))

    return edited_rows


def render_output_editor(parsed_rows, grouped_days, output_edits, key_suffix="0"):
    """
    User-facing editor for generated output text.
    Edits update the preview, HTML download, and PDF export.
    """

    st.subheader("Edit generated itinerary")
    st.caption("Edit the generated output here before downloading HTML or creating the PDF. The raw Excel input above is not changed.")

    with st.expander("Edit cover and summary pages", expanded=False):
        output_edits["trip_title"] = st.text_input(
            "Cover title",
            value=output_edits.get("trip_title", ""),
            key=f"edit_trip_title_{key_suffix}",
        )
        output_edits["trip_subtitle"] = st.text_area(
            "Cover subtitle",
            value=output_edits.get("trip_subtitle", ""),
            height=80,
            key=f"edit_trip_subtitle_{key_suffix}",
        )
        output_edits["destinations_line"] = st.text_input(
            "Destinations line",
            value=output_edits.get("destinations_line", ""),
            key=f"edit_destinations_line_{key_suffix}",
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
                    key=f"edit_{key_suffix}_{day}_title",
                )
                day_edit["city"] = st.text_input(
                    f"{day} city",
                    value=day_edit.get("city", get_primary_city(rows)),
                    key=f"edit_{key_suffix}_{day}_city",
                )
                day_edit["intro"] = st.text_area(
                    f"{day} intro",
                    value=day_edit.get("intro", create_day_intro(rows)),
                    height=95,
                    key=f"edit_{key_suffix}_{day}_intro",
                )

                with st.expander(f"Edit {day} itinerary items", expanded=False):
                    for index, row in enumerate(rows, start=1):
                        row_id = row.get("row_id") or f'{day}_{index}'
                        row_edit = output_edits.setdefault("rows", {}).setdefault(row_id, {})
                        row_type = get_row_type(row)
                        item_label = row_edit.get("title") or row.get("title") or f"Item {index}"

                        with st.expander(f"{index}. {row_type}: {item_label}", expanded=False):
                            row_edit["title"] = st.text_input(
                                "Title / text",
                                value=row_edit.get("title", row.get("title", "")),
                                key=f"edit_{key_suffix}_{row_id}_title",
                            )
                            row_edit["city"] = st.text_input(
                                "City / location",
                                value=row_edit.get("city", row.get("city", "")),
                                key=f"edit_{key_suffix}_{row_id}_city",
                            )

                            col1, col2 = st.columns(2)
                            with col1:
                                row_edit["time"] = st.text_input(
                                    "Time",
                                    value=row_edit.get("time", row.get("time", "")),
                                    key=f"edit_{key_suffix}_{row_id}_time",
                                )
                                row_edit["meeting_point"] = st.text_input(
                                    "Meeting point",
                                    value=row_edit.get("meeting_point", row.get("meeting_point", "")),
                                    key=f"edit_{key_suffix}_{row_id}_meeting",
                                )
                            with col2:
                                row_edit["end_point"] = st.text_input(
                                    "End point",
                                    value=row_edit.get("end_point", row.get("end_point", "")),
                                    key=f"edit_{key_suffix}_{row_id}_end",
                                )
                                row_edit["luggage_included"] = st.text_input(
                                    "Luggage included",
                                    value=row_edit.get("luggage_included", row.get("luggage_included", "")),
                                    key=f"edit_{key_suffix}_{row_id}_luggage",
                                )

                            row_edit["notable_sights_text"] = st.text_area(
                                "Notable sights, one per line",
                                value=row_edit.get("notable_sights_text", list_to_text(row.get("notable_sights", []))),
                                height=90,
                                key=f"edit_{key_suffix}_{row_id}_sights",
                            )
                            row_edit["includes_text"] = st.text_area(
                                "Inclusions, one per line",
                                value=row_edit.get("includes_text", list_to_text(row.get("includes", []))),
                                height=100,
                                key=f"edit_{key_suffix}_{row_id}_includes",
                            )

    with st.expander("Edit final inclusion / exclusion pages", expanded=False):
        output_edits["whats_included_text"] = st.text_area(
            "What’s included, one item per line",
            value=output_edits.get("whats_included_text", ""),
            height=220,
            key=f"edit_whats_included_text_{key_suffix}",
        )
        output_edits["whats_not_included_text"] = st.text_area(
            "What’s not included, one item per line",
            value=output_edits.get("whats_not_included_text", ""),
            height=180,
            key=f"edit_whats_not_included_text_{key_suffix}",
        )

def build_itinerary_html(parsed_rows, grouped_days, output_edits=None):
    output_edits = output_edits or {}

    trip_title = output_edits.get("trip_title") or create_trip_title(parsed_rows, grouped_days)
    trip_subtitle = output_edits.get("trip_subtitle") or create_trip_subtitle(parsed_rows, grouped_days)
    destinations_line = output_edits.get("destinations_line") or create_destinations_line(parsed_rows)
    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    journey_arc = create_journey_arc(grouped_days)

    if output_edits.get("whats_included_text"):
        whats_included = text_to_list(output_edits.get("whats_included_text"))
    else:
        whats_included = create_whats_included(parsed_rows, grouped_days)

    activity_inclusions = create_activity_inclusions(parsed_rows)

    if output_edits.get("whats_not_included_text"):
        whats_not_included = text_to_list(output_edits.get("whats_not_included_text"))
    else:
        whats_not_included = create_whats_not_included(parsed_rows)

    html_text = f"""
    <style>
        .preview-background {{
            background: #11151b;
            padding: 32px 0 60px 0;
        }}

        .a4-page {{
            width: 794px;
            min-height: 1123px;
            background: #f4efe8;
            color: #1f3446;
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
            color: #7b746c;
            margin-bottom: 18px;
        }}

        .cover-title {{
            font-size: 54px;
            line-height: 1.05;
            font-weight: 700;
            color: #1f3446;
            margin-bottom: 18px;
        }}

        .cover-subtitle {{
            font-size: 24px;
            line-height: 1.25;
            color: #1f3446;
            margin-bottom: 18px;
        }}

        .cover-destinations {{
            font-family: Arial, sans-serif;
            font-size: 15px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #2f2f2f;
            margin-top: 24px;
        }}

        .glance-card,
        .journey-arc {{
            background: rgba(255, 255, 255, 0.34);
            border: 1px solid #d8cec2;
            padding: 28px;
        }}

        .glance-card {{
            margin-bottom: 34px;
        }}

        .glance-title,
        .journey-title {{
            font-size: 30px;
            margin-bottom: 16px;
            color: #1f3446;
        }}

        .glance-row {{
            display: grid;
            grid-template-columns: 165px 1fr;
            gap: 18px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.45;
            padding: 8px 0;
            border-bottom: 1px solid rgba(216, 206, 194, 0.7);
        }}

        .glance-label {{
            font-weight: 700;
            color: #1f3446;
        }}

        .glance-value {{
            color: #2f2f2f;
        }}

        .journey-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #2f2f2f;
        }}

        .journey-table th {{
            text-align: left;
            color: #1f3446;
            font-weight: 700;
            padding: 10px 8px;
            border-bottom: 1px solid #c9beb1;
        }}

        .journey-table td {{
            padding: 12px 8px;
            vertical-align: top;
            border-bottom: 1px solid rgba(216, 206, 194, 0.7);
            line-height: 1.45;
        }}

        .journey-days {{
            white-space: nowrap;
        }}

        .day-label {{
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #1f3446;
        }}

        .day-title {{
            font-size: 27px;
            font-weight: 500;
            margin-bottom: 12px;
            color: #1f3446;
        }}

        .city {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #7b746c;
            margin-bottom: 20px;
        }}

        .intro {{
            font-size: 15px;
            line-height: 1.5;
            margin-bottom: 22px;
            color: #2f2f2f;
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
            color: #1f3446;
        }}

        .small-section {{
            margin-top: 10px;
        }}

        .body-text {{
            font-size: 13.5px;
            line-height: 1.38;
            color: #2f2f2f;
            margin-bottom: 5px;
        }}

        .strong-line {{
            font-weight: 600;
        }}

        .meta-label {{
            font-family: Arial, sans-serif;
            font-weight: 700;
            font-size: 12px;
            color: #1f3446;
        }}

        .final-page-title {{
            font-size: 34px;
            margin-bottom: 22px;
            color: #1f3446;
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
            color: #1f3446;
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
            color: #2f2f2f;
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

    <div class="preview-background">

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
    outputs_folder = Path("outputs")
    outputs_folder.mkdir(exist_ok=True)

    output_path = outputs_folder / "itinerary_preview.html"
    full_html = build_full_html_document(itinerary_html)

    output_path.write_text(full_html, encoding="utf-8")

    return output_path


def save_pdf_file(html_path):
    outputs_folder = Path("outputs")
    outputs_folder.mkdir(exist_ok=True)

    pdf_path = outputs_folder / "itinerary_preview.pdf"

    export_html_to_pdf(html_path, pdf_path)

    return pdf_path


def get_duplicate_count(raw_text_value):
    raw_rows = [
        line for line in raw_text_value.splitlines()
        if line.strip().lower().startswith("day ")
    ]

    parsed_rows = parse_itinerary(raw_text_value)

    return max(len(raw_rows) - len(parsed_rows), 0)



def build_current_outputs():
    """Rebuilds HTML and output file paths from the current editable state."""

    edited_rows = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    html_text = build_itinerary_html(
        edited_rows,
        edited_grouped_days,
        st.session_state.output_edits,
    )

    st.session_state.itinerary_html = html_text
    st.session_state.html_path = save_html_file(html_text)

    return edited_rows, edited_grouped_days


def make_project_data():
    return {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_text": st.session_state.get("raw_text_input", ""),
        "output_edits": st.session_state.get("output_edits", {}),
    }


def make_project_json_bytes():
    return json.dumps(make_project_data(), ensure_ascii=False, indent=2).encode("utf-8")


def load_project_data(project_data):
    raw_project_text = str(project_data.get("raw_text", "")).strip()

    if not raw_project_text:
        raise ValueError("The project file does not contain raw itinerary text.")

    parsed_rows = parse_itinerary(raw_project_text)

    if not parsed_rows:
        raise ValueError("The project raw text could not be parsed into itinerary rows.")

    grouped_days = group_rows_by_day(parsed_rows)
    output_edits = project_data.get("output_edits")

    if not isinstance(output_edits, dict):
        output_edits = make_output_edit_state(parsed_rows, grouped_days)

    st.session_state.parsed_rows = parsed_rows
    st.session_state.output_edits = output_edits
    st.session_state.last_generated_raw_text = raw_project_text
    st.session_state.pdf_bytes = None
    st.session_state.editor_revision += 1
    build_current_outputs()

    return parsed_rows, grouped_days


def estimate_day_weight(day, rows, output_edits):
    """
    Lightweight visual-weight estimate for one A4 day page.
    This does not block export; it only warns when a page may become crowded.
    """

    day_edit = (output_edits or {}).get("days", {}).get(day, {})
    row_edits = (output_edits or {}).get("rows", {})
    title = day_edit.get("title") or create_day_title(rows)
    intro = day_edit.get("intro") or create_day_intro(rows)

    weight = 18
    weight += len(title) / 28
    weight += len(intro) / 75

    included_count = 0

    for row in rows:
        row_id = row.get("row_id") or f'line_{row.get("line_number", "")}'
        edits = row_edits.get(row_id, {})
        row_type = get_row_type(row)
        title_text = edits.get("title", row.get("title", ""))

        if row_type in ["Arrival", "Hotel"] or (row_type == "Transfer" and not is_self_transfer(row)):
            included_count += 1
            weight += 2.2 + len(title_text) / 65
            continue

        weight += 5 + len(title_text) / 50

        for key in ["time", "meeting_point", "end_point", "luggage_included"]:
            value = edits.get(key, row.get(key, ""))
            if value:
                weight += 1.7 + len(value) / 90

        sights = text_to_list(edits.get("notable_sights_text", list_to_text(row.get("notable_sights", []))))
        includes = text_to_list(edits.get("includes_text", list_to_text(row.get("includes", []))))

        if row_type == "Activity" and sights:
            weight += 2 + len(sights) * 1.35

        if row_type in TRANSPORT_TYPES and includes:
            weight += 2 + len(includes) * 1.35

        if is_self_transfer(row):
            weight += 5

    if included_count:
        weight += 4 + included_count * 1.45

    return weight


def find_page_warnings(edited_rows, edited_grouped_days, output_edits):
    warnings = []

    for day, rows in edited_grouped_days.items():
        weight = estimate_day_weight(day, rows, output_edits)

        if weight >= 78:
            warnings.append(
                f"{day} may be too full for one A4 page. Consider shortening the intro, free-time text, or included-today details."
            )
        elif weight >= 68:
            warnings.append(
                f"{day} is close to the practical A4 limit. Review it before exporting."
            )

    activity_count = len(create_activity_inclusions(edited_rows))
    if activity_count > 14:
        warnings.append("The Activity inclusions section is long and may require several PDF pages.")

    return warnings


def initialise_state():
    defaults = {
        "itinerary_html": "",
        "html_path": None,
        "pdf_bytes": None,
        "parsed_rows": [],
        "output_edits": {},
        "last_generated_raw_text": "",
        "editor_revision": 0,
        "pending_project_data": None,
        "project_loaded_message": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialise_state()

if st.session_state.get("pending_project_data"):
    try:
        parsed_rows, grouped_days = load_project_data(st.session_state.pending_project_data)
        st.session_state.project_loaded_message = (
            f"Loaded editable project with {len(parsed_rows)} rows across {len(grouped_days)} days."
        )
    except Exception as error:
        st.session_state.project_load_error = str(error)
    finally:
        st.session_state.pending_project_data = None

if st.session_state.get("project_loaded_message"):
    st.success(st.session_state.project_loaded_message)
    st.session_state.project_loaded_message = ""

input_col, action_col = st.columns([2, 1])

with action_col:
    st.markdown("### Generate")
    generate_clicked = st.button("Generate itinerary", type="primary", use_container_width=True)

with input_col:
    st.caption("After generating, use the editor below to adjust the output before exporting.")

if generate_clicked:
    if raw_text.strip():
        parsed_rows = parse_itinerary(raw_text)
        grouped_days = group_rows_by_day(parsed_rows)
        duplicate_count = get_duplicate_count(raw_text)

        if not parsed_rows:
            st.error("No valid itinerary rows were found. Please check that the pasted text starts with Day 1, Day 2, etc.")
        else:
            st.session_state.parsed_rows = parsed_rows
            st.session_state.output_edits = make_output_edit_state(parsed_rows, grouped_days)
            st.session_state.last_generated_raw_text = raw_text
            st.session_state.pdf_bytes = None
            st.session_state.editor_revision += 1
            build_current_outputs()

            st.success(f"Parsed {len(parsed_rows)} itinerary rows across {len(grouped_days)} days.")

            if duplicate_count:
                st.warning(f"Skipped {duplicate_count} duplicate or malformed row(s).")

            with st.expander("Structured parser preview"):
                st.dataframe(parsed_rows, use_container_width=True)

            with st.expander("Day grouping debug"):
                for day, rows in grouped_days.items():
                    st.write(f"{day}: {len(rows)} rows")
                    for row in rows:
                        st.write(
                            f"- {row.get('type')} / {row.get('effective_type')}: "
                            f"{row.get('title')} ({row.get('city')})"
                        )

            st.success(f"HTML file created: {st.session_state.html_path}")

    else:
        st.warning("Please paste some itinerary text first.")

if st.session_state.parsed_rows and st.session_state.output_edits:
    edited_rows_for_editor = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_for_editor = group_rows_by_day(edited_rows_for_editor)

    editor_top_left, editor_top_right = st.columns([2, 1])
    with editor_top_left:
        st.markdown("### Edit generated output")
        st.caption("Your edits affect the preview, HTML download, project JSON, and PDF export. The raw Excel input is kept unchanged.")
    with editor_top_right:
        if st.button("Reset edits to generated text", use_container_width=True):
            original_grouped_days = group_rows_by_day(st.session_state.parsed_rows)
            st.session_state.output_edits = make_output_edit_state(st.session_state.parsed_rows, original_grouped_days)
            st.session_state.pdf_bytes = None
            st.session_state.editor_revision += 1
            build_current_outputs()
            st.rerun()

    render_output_editor(
        st.session_state.parsed_rows,
        edited_grouped_for_editor,
        st.session_state.output_edits,
        key_suffix=str(st.session_state.editor_revision),
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

    st.session_state.itinerary_html = rebuilt_html
    st.session_state.html_path = save_html_file(st.session_state.itinerary_html)

if st.session_state.itinerary_html:
    st.subheader("Preview and export")

    html_path = Path(st.session_state.html_path)
    edited_rows_for_export = apply_output_edits(st.session_state.parsed_rows, st.session_state.output_edits)
    edited_grouped_for_export = group_rows_by_day(edited_rows_for_export)
    page_warnings = find_page_warnings(edited_rows_for_export, edited_grouped_for_export, st.session_state.output_edits)

    if page_warnings:
        with st.expander("Export checks", expanded=True):
            for warning in page_warnings:
                st.warning(warning)
    else:
        st.success("Export checks passed. No crowded A4 pages detected by the layout estimator.")

    project_col, html_col, pdf_col = st.columns(3)

    with project_col:
        st.download_button(
            label="Download editable project JSON",
            data=make_project_json_bytes(),
            file_name="itinerary_project.json",
            mime="application/json",
            use_container_width=True,
        )

    with html_col:
        with open(html_path, "rb") as html_file:
            st.download_button(
                label="Download HTML preview",
                data=html_file,
                file_name="itinerary_preview.html",
                mime="text/html",
                use_container_width=True,
            )

    with pdf_col:
        create_pdf_clicked = st.button("Create PDF", use_container_width=True)

    if create_pdf_clicked:
        try:
            with st.spinner("Creating PDF..."):
                pdf_path = save_pdf_file(html_path)
                st.session_state.pdf_bytes = Path(pdf_path).read_bytes()

            st.success("PDF created. Your browser should start the download automatically.")
            auto_download_file(
                st.session_state.pdf_bytes,
                "itinerary_preview.pdf",
                "application/pdf",
            )

        except Exception as error:
            st.error(
                "PDF export failed in this environment. The itinerary preview, HTML download, and project JSON still work."
            )
            with st.expander("PDF export error details"):
                st.exception(error)

    if st.session_state.pdf_bytes:
        st.download_button(
            label="Download PDF again",
            data=st.session_state.pdf_bytes,
            file_name="itinerary_preview.pdf",
            mime="application/pdf",
        )

    st.html(st.session_state.itinerary_html)
