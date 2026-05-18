import streamlit as st
from parser import parse_itinerary
from generator import group_rows_by_day, create_day_title, create_day_intro

st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide"
)

st.title("Itinerary Creator")

st.write(
    "Paste raw Excel itinerary text below. "
    "The app will turn it into a polished itinerary preview."
)

raw_text = st.text_area(
    "Raw Excel text",
    height=260,
    placeholder="Paste itinerary rows here..."
)


def build_itinerary_html(grouped_days):
    html = """
    <style>
        .itinerary-wrapper {
            background: #f4efe8;
            color: #1f3446;
            padding: 48px;
            max-width: 850px;
            margin: 32px auto;
            font-family: Georgia, 'Times New Roman', serif;
        }

        .day-card {
            padding: 34px 0;
            border-bottom: 1px solid #d8cec2;
        }

        .day-label {
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 4px;
            color: #1f3446;
        }

        .day-title {
            font-size: 27px;
            font-weight: 500;
            margin-bottom: 10px;
            color: #1f3446;
        }

        .city {
            font-family: Arial, sans-serif;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #7b746c;
            margin-bottom: 18px;
        }

        .intro {
            font-size: 16px;
            line-height: 1.55;
            margin-bottom: 24px;
            color: #2f2f2f;
        }

        .section-title {
            font-family: Arial, sans-serif;
            font-size: 14px;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 6px;
            color: #1f3446;
        }

        .body-text {
            font-size: 15px;
            line-height: 1.45;
            color: #2f2f2f;
            margin-bottom: 5px;
        }

        ul {
            margin-top: 6px;
            margin-bottom: 14px;
        }

        li {
            font-size: 15px;
            line-height: 1.45;
            margin-bottom: 4px;
            color: #2f2f2f;
        }
    </style>

    <div class="itinerary-wrapper">
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
        <div class="day-card">
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


if st.button("Generate itinerary"):
    if raw_text.strip():
        parsed_rows = parse_itinerary(raw_text)
        grouped_days = group_rows_by_day(parsed_rows)

        st.success(f"Parsed {len(parsed_rows)} itinerary rows.")

        with st.expander("Structured parser preview"):
            st.dataframe(parsed_rows, use_container_width=True)

        st.subheader("Styled itinerary preview")

        itinerary_html = build_itinerary_html(grouped_days)
        st.html(itinerary_html)

    else:
        st.warning("Please paste some itinerary text first.")