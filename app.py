import streamlit as st
from parser import parse_itinerary
from generator import group_rows_by_day, create_day_title

st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide"
)

st.title("Itinerary Creator")

st.write(
    "Paste raw Excel itinerary text below. "
    "The app will turn it into structured itinerary data."
)

raw_text = st.text_area(
    "Raw Excel text",
    height=260,
    placeholder="Paste itinerary rows here..."
)

if st.button("Generate itinerary"):
    if raw_text.strip():
        parsed_rows = parse_itinerary(raw_text)
        grouped_days = group_rows_by_day(parsed_rows)

        st.success(f"Parsed {len(parsed_rows)} itinerary rows.")

        with st.expander("Structured parser preview"):
            st.dataframe(parsed_rows, use_container_width=True)

        st.subheader("Itinerary preview")

        for day, rows in grouped_days.items():
            day_title = create_day_title(rows)
            city = rows[0].get("city", "")

            st.markdown("---")
            st.markdown(f"## {day}")
            st.markdown(f"### {day_title}")

            if city:
                st.caption(city)

            included_items = []

            for row in rows:
                item_type = row.get("type", "")
                title = row.get("title", "")
                time = row.get("time", "")
                meeting_point = row.get("meeting_point", "")
                end_point = row.get("end_point", "")
                includes = row.get("includes", [])

                if item_type in ["Arrival", "Departure"]:
                    st.write(title)

                elif item_type == "Transfer":
                    included_items.append(title)

                elif item_type == "Hotel":
                    included_items.append(title)

                elif item_type == "Activity":
                    st.markdown("**Featured experience**")
                    st.write(title)

                    if time:
                        st.write(f"Time: {time}")

                    if meeting_point:
                        st.write(f"Meeting point: {meeting_point}")

                    if end_point:
                        st.write(f"End point: {end_point}")

                    if includes:
                        st.markdown("**Includes**")
                        for item in includes:
                            st.markdown(f"- {item}")

                elif item_type == "Leisure":
                    st.markdown("**Your free time**")
                    st.write(title)

                else:
                    st.write(title)

            if included_items:
                st.markdown("**Included today**")
                for item in included_items:
                    st.markdown(f"- {item}")

    else:
        st.warning("Please paste some itinerary text first.")