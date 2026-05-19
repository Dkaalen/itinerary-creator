from pathlib import Path
import re
import streamlit as st
from parser import parse_itinerary
from pdf_exporter import export_html_to_pdf
from generator import (
    group_rows_by_day,
    get_row_type,
    TRANSPORT_TYPES,
    create_day_title,
    create_day_intro,
    create_trip_title,
    create_trip_subtitle,
    create_destinations_line,
    create_trip_glance,
    create_journey_arc,
    create_whats_included,
    create_whats_not_included,
    create_final_note,
)

st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide"
)

st.title("Itinerary Creator")

st.write(
    "Paste raw Excel itinerary text below. "
    "The app will turn it into a polished A4 itinerary preview."
)

st.caption("Fix version: 2026-05-19 v7 one-click PDF download")

raw_text = st.text_area(
    "Raw Excel text",
    height=300,
    placeholder="Paste itinerary rows here..."
)


def normalize_list(items):
    if not items:
        return []

    if isinstance(items, list):
        return [item.strip() for item in items if item and item.strip()]

    if isinstance(items, str):
        return [item.strip() for item in items.split(",") if item.strip()]

    return []


def render_list_items(items):
    clean_items = normalize_list(items)

    if not clean_items:
        return ""

    html = "<ul>"

    for item in clean_items:
        html += f"<li>{item}</li>"

    html += "</ul>"

    return html


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
    title = row.get("title", "")
    time = row.get("time", "")
    meeting_point = row.get("meeting_point", "")
    end_point = row.get("end_point", "")
    notable_sights = normalize_list(row.get("notable_sights", []))
    includes = normalize_list(row.get("includes", []))

    html = f'<div class="section-title">{get_time_period(time)}</div>'
    html += f'<div class="body-text strong-line">{title}</div>'

    if time:
        html += f'<div class="body-text">Time: {time}</div>'

    if meeting_point:
        html += f'<div class="body-text">Meeting point: {meeting_point}</div>'

    if end_point:
        html += f'<div class="body-text">End point: {end_point}</div>'

    if notable_sights:
        html += '<div class="section-title">Notable sights</div>'
        html += render_list_items(notable_sights)

    if includes:
        html += '<div class="section-title">Includes</div>'
        html += render_list_items(includes)

    return {
        "kind": "activity",
        "html": html,
    }


def build_transport_block(row):
    title = row.get("title", "")
    time = row.get("time", "")
    includes = normalize_list(row.get("includes", []))
    luggage_included = row.get("luggage_included", "")

    html = '<div class="section-title">Travel today</div>'
    html += f'<div class="body-text strong-line">{title}</div>'

    if time:
        html += f'<div class="body-text">Time: {time}</div>'

    if luggage_included:
        html += f'<div class="body-text">Luggage included: {luggage_included}</div>'

    if includes:
        html += '<div class="section-title">Includes</div>'
        html += render_list_items(includes)

    return {
        "kind": "transport",
        "html": html,
    }


def build_leisure_block():
    html = '<div class="section-title">Your free time</div>'
    html += (
        '<div class="body-text">'
        'Take this time at your own pace. You may want to explore nearby sights, '
        'enjoy a relaxed meal, or simply settle into the destination.'
        '</div>'
    )

    return {
        "kind": "leisure",
        "html": html,
    }


def build_included_today_block(items):
    html = '<div class="section-title">Included today</div>'
    html += render_list_items(items)

    return {
        "kind": "included",
        "html": html,
    }


def build_day_blocks(rows):
    blocks = []
    included_items = []

    for row in rows:
        row_type = get_row_type(row)
        title = row.get("title", "")

        if row_type in ["Arrival", "Transfer", "Hotel"]:
            included_items.append(title)

        elif row_type == "Departure":
            continue

        elif row_type in TRANSPORT_TYPES:
            blocks.append(build_transport_block(row))

        elif row_type == "Activity":
            blocks.append(build_activity_block(row))

        elif row_type == "Leisure":
            blocks.append(build_leisure_block())

        else:
            included_items.append(title)

    if included_items:
        blocks.append(build_included_today_block(included_items))

    return blocks


def block_score(block):
    html = block.get("html", "")

    score = 1
    score += html.count("<li>") * 1
    score += html.count('class="body-text"') * 1

    if block.get("kind") in ["activity", "transport"]:
        score += 4

    return score


def split_day_blocks(blocks):
    """
    Conservative page splitting.
    Normal days stay on one page.
    Heavy days split by block, never by day mixing.
    """

    total_score = sum(block_score(block) for block in blocks)

    if total_score <= 34:
        return [blocks]

    pages = []
    current_page = []
    current_score = 0

    for block in blocks:
        score = block_score(block)

        if current_page and current_score + score > 34:
            pages.append(current_page)
            current_page = [block]
            current_score = score
        else:
            current_page.append(block)
            current_score += score

    if current_page:
        pages.append(current_page)

    return pages


def render_day_pages(day, rows):
    day_title = create_day_title(rows)
    day_intro = create_day_intro(rows)
    city = rows[0].get("city", "") if rows else ""

    blocks = build_day_blocks(rows)
    pages = split_day_blocks(blocks)

    html = ""

    for page_index, page_blocks in enumerate(pages):
        continued_label = "" if page_index == 0 else " continued"

        html += f"""
        <div class="a4-page">
            <div class="day-label">{day}{continued_label}</div>
            <div class="day-title">{day_title}</div>
            <div class="city">{city}</div>
        """

        if page_index == 0:
            html += f'<div class="intro">{day_intro}</div>'

        for block in page_blocks:
            html += block["html"]

        html += """
        </div>
        """

    return html


def render_split_list_pages(title, items, items_per_page=22):
    html = ""
    clean_items = normalize_list(items)

    for start in range(0, len(clean_items), items_per_page):
        chunk = clean_items[start:start + items_per_page]
        continued = "" if start == 0 else " continued"

        html += f"""
        <div class="a4-page">
            <div class="final-page-title">{title}{continued}</div>
            {render_list_items(chunk)}
        </div>
        """

    return html



def create_activity_inclusions(parsed_rows):
    """
    Creates a separate client-facing list of activities and their inclusions.
    This keeps day-by-day pages clean while preserving the practical details.
    """

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
            html_text += '</div>'

        html_text += '</div>'

    return html_text


def auto_download_file(file_bytes, file_name, mime_type):
    """
    Triggers a browser download after a Streamlit button click.
    A normal st.download_button is still shown as a fallback below it.
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

    html = f"""
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
            padding: 70px 66px;
            box-sizing: border-box;
            font-family: Georgia, 'Times New Roman', serif;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
            page-break-after: always;
        }}

        .cover-page {{
            min-height: 1123px;
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

        .glance-card {{
            background: rgba(255, 255, 255, 0.42);
            padding: 28px;
            margin-bottom: 34px;
            border: 1px solid #d8cec2;
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

        .journey-arc {{
            padding: 28px;
            background: rgba(255, 255, 255, 0.28);
            border: 1px solid #d8cec2;
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

        .section-title {{
            font-family: Arial, sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            margin-top: 15px;
            margin-bottom: 5px;
            color: #1f3446;
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

        .final-page-title {{
            font-size: 34px;
            margin-bottom: 22px;
            color: #1f3446;
        }}

        .final-note {{
            font-size: 17px;
            line-height: 1.6;
            color: #2f2f2f;
            margin-top: 18px;
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
                min-height: 297mm;
                margin: 0;
                box-shadow: none;
                page-break-after: always;
            }}
        }}
    </style>

    <div class="preview-background">

        <div class="a4-page cover-page">
            <div class="cover-kicker">Curated Travel Itinerary</div>
            <div class="cover-title">{trip_title}</div>
            <div class="cover-subtitle">{trip_subtitle}</div>
            <div class="cover-destinations">{destinations_line}</div>
        </div>

        <div class="a4-page">
            <div class="glance-card">
                <div class="glance-title">Your Trip at a Glance</div>
    """

    for label, value in trip_glance.items():
        html += f"""
                <div class="glance-row">
                    <div class="glance-label">{label}</div>
                    <div class="glance-value">{value}</div>
                </div>
        """

    html += """
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
        html += f"""
                        <tr>
                            <td>{chapter["chapter"]}</td>
                            <td class="journey-days">{chapter["days"]}</td>
                            <td>{chapter["experience"]}</td>
                        </tr>
        """

    html += """
                    </tbody>
                </table>
            </div>
        </div>
    """

    for day, rows in grouped_days.items():
        html += render_day_pages(day, rows)

    html += render_split_list_pages("What’s included", whats_included)
    html += render_split_list_pages("What’s not included", whats_not_included)

    html += f"""
        <div class="a4-page">
            <div class="final-page-title">Final Note</div>
            <div class="final-note">{final_note}</div>
        </div>
    """

    html += "</div>"

    return html


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
