from pathlib import Path
import base64
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


APP_VERSION = "2026-05-19 v10 clean original merge"


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

raw_text = st.text_area(
    "Raw Excel text",
    height=300,
    placeholder="Paste itinerary rows here...",
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

        if row_type in ["Arrival", "Transfer", "Hotel", "Departure"]:
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


def render_day_pages(day, rows):
    """
    One itinerary day renders as one A4 page.
    This deliberately avoids the earlier manual page splitter, which caused
    day-boundary bleed/duplication.
    """

    day_title = create_day_title(rows)
    day_intro = create_day_intro(rows)
    city = get_primary_city(rows)
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


def build_itinerary_html(parsed_rows, grouped_days):
    trip_title = create_trip_title(parsed_rows, grouped_days)
    trip_subtitle = create_trip_subtitle(parsed_rows, grouped_days)
    destinations_line = create_destinations_line(parsed_rows)
    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    journey_arc = create_journey_arc(grouped_days)
    whats_included = create_whats_included(parsed_rows, grouped_days)
    activity_inclusions = create_activity_inclusions(parsed_rows)
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
        html_text += render_day_pages(day, rows)

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


if "itinerary_html" not in st.session_state:
    st.session_state.itinerary_html = ""

if "html_path" not in st.session_state:
    st.session_state.html_path = None

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

if st.button("Generate itinerary"):
    if raw_text.strip():
        parsed_rows = parse_itinerary(raw_text)
        grouped_days = group_rows_by_day(parsed_rows)
        duplicate_count = get_duplicate_count(raw_text)

        st.session_state.itinerary_html = build_itinerary_html(parsed_rows, grouped_days)
        st.session_state.html_path = save_html_file(st.session_state.itinerary_html)
        st.session_state.pdf_bytes = None

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

if st.session_state.itinerary_html:
    st.subheader("A4 itinerary preview")

    html_path = Path(st.session_state.html_path)

    with open(html_path, "rb") as html_file:
        st.download_button(
            label="Download HTML preview",
            data=html_file,
            file_name="itinerary_preview.html",
            mime="text/html",
        )

    if st.button("Create PDF"):
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
                "PDF export failed in this environment. The itinerary preview and HTML download still work. "
                "If this happens on Streamlit Cloud, check the app logs for the Playwright/Chromium error."
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
