from pathlib import Path
import streamlit as st
from parser import parse_itinerary
from pdf_exporter import export_html_to_pdf
from generator import (
    group_rows_by_day,
    create_day_title,
    create_day_intro,
    create_trip_title,
    create_trip_subtitle,
    create_destinations_line,
    create_trip_glance,
    create_journey_arc,
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

raw_text = st.text_area(
    "Raw Excel text",
    height=300,
    placeholder="Paste itinerary rows here..."
)


def build_itinerary_html(parsed_rows, grouped_days):
    trip_title = create_trip_title(parsed_rows, grouped_days)
    trip_subtitle = create_trip_subtitle(parsed_rows, grouped_days)
    destinations_line = create_destinations_line(parsed_rows)
    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    journey_arc = create_journey_arc(grouped_days)

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
            padding: 64px;
            box-sizing: border-box;
            font-family: Georgia, 'Times New Roman', serif;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
            page-break-after: always;
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

        .glance-card {{
            background: rgba(255, 255, 255, 0.42);
            padding: 28px;
            margin-bottom: 34px;
            border: 1px solid #d8cec2;
        }}

        .glance-title {{
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

        .journey-title {{
            font-size: 30px;
            margin-bottom: 18px;
            color: #1f3446;
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
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #1f3446;
        }}

        .day-title {{
            font-size: 29px;
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
            margin-bottom: 22px;
        }}

        .intro {{
            font-size: 16px;
            line-height: 1.55;
            margin-bottom: 24px;
            color: #2f2f2f;
        }}

        .section-title {{
            font-family: Arial, sans-serif;
            font-size: 14px;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 7px;
            color: #1f3446;
        }}

        .body-text {{
            font-size: 15px;
            line-height: 1.45;
            color: #2f2f2f;
            margin-bottom: 6px;
        }}

        ul {{
            margin-top: 6px;
            margin-bottom: 14px;
        }}

        li {{
            font-size: 15px;
            line-height: 1.45;
            margin-bottom: 4px;
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
        day_title = create_day_title(rows)
        day_intro = create_day_intro(rows)
        city = rows[0].get("city", "") if rows else ""

        included_items = []
        day_content = ""

        for row in rows:
            item_type = row.get("type", "")
            title = row.get("title", "")
            time = row.get("time", "")
            meeting_point = row.get("meeting_point", "")
            end_point = row.get("end_point", "")
            includes = row.get("includes", [])

            if item_type in ["Arrival", "Departure", "Transfer", "Hotel"]:
                included_items.append(title)

            elif item_type == "Activity":
                day_content += '<div class="section-title">Featured experience</div>'
                day_content += f'<div class="body-text">{title}</div>'

                if time:
                    day_content += f'<div class="body-text">Time: {time}</div>'

                if meeting_point:
                    day_content += f'<div class="body-text">Meeting point: {meeting_point}</div>'

                if end_point:
                    day_content += f'<div class="body-text">End point: {end_point}</div>'

                if includes:
                    day_content += '<div class="section-title">Includes</div>'
                    day_content += "<ul>"
                    for item in includes:
                        day_content += f"<li>{item}</li>"
                    day_content += "</ul>"

            elif item_type == "Leisure":
                day_content += '<div class="section-title">Your free time</div>'
                day_content += (
                    '<div class="body-text">'
                    'Take this time at your own pace. You may want to explore nearby sights, '
                    'enjoy a relaxed meal, or simply settle into the destination.'
                    '</div>'
                )

            else:
                included_items.append(title)

        html += f"""
        <div class="a4-page">
            <div class="day-label">{day}</div>
            <div class="day-title">{day_title}</div>
            <div class="city">{city}</div>
            <div class="intro">{day_intro}</div>
            {day_content}
        """

        if included_items:
            html += '<div class="section-title">Included today</div>'
            html += "<ul>"
            for item in included_items:
                html += f"<li>{item}</li>"
            html += "</ul>"

        html += "</div>"

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


if st.button("Generate itinerary"):
    if raw_text.strip():
        parsed_rows = parse_itinerary(raw_text)
        grouped_days = group_rows_by_day(parsed_rows)

        st.success(f"Parsed {len(parsed_rows)} itinerary rows.")

        with st.expander("Structured parser preview"):
            st.dataframe(parsed_rows, use_container_width=True)

        st.subheader("A4 itinerary preview")

        itinerary_html = build_itinerary_html(parsed_rows, grouped_days)

        html_path = save_html_file(itinerary_html)
        pdf_path = save_pdf_file(html_path)

        st.success(f"HTML file created: {html_path}")
        st.success(f"PDF file created: {pdf_path}")

        with open(html_path, "rb") as html_file:
            st.download_button(
                label="Download HTML preview",
                data=html_file,
                file_name="itinerary_preview.html",
                mime="text/html"
            )

        with open(pdf_path, "rb") as pdf_file:
            st.download_button(
                label="Download PDF preview",
                data=pdf_file,
                file_name="itinerary_preview.pdf",
                mime="application/pdf"
            )

        st.html(itinerary_html)

    else:
        st.warning("Please paste some itinerary text first.")