import streamlit as st

from generator import (
    TRANSPORT_TYPES,
    create_activity_inclusions,
    create_client_activity_title,
    get_row_type,
    group_rows_by_day,
    is_self_arranged,
)
from ui.day_rendering import get_activity_logistics, is_self_arranged_transport
from ui.output_edits import apply_output_edits, apply_rich_writing_to_all_days, mark_output_dirty


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
    self_arranged = [row for row in parsed_rows if is_self_arranged_transport(row)]

    return {
        "days": len(grouped_days),
        "destinations": len(destinations),
        "destination_names": destinations,
        "activities": len(activities),
        "hotels": len(hotels),
        "self_arranged": len(self_arranged),
        "optional_rows": len(optional_rows),
    }


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
        (True, "Activity details shown inline"),
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

    st.subheader("Writing assistant")
    st.caption("Runs automatically on generation. Use this again after manual edits if you want to refresh the day text.")
    if st.button("Improve day-to-day text", key="sidebar_assistant_improve_all", use_container_width=True):
        st.session_state.output_edits = apply_rich_writing_to_all_days(
            st.session_state.parsed_rows,
            st.session_state.output_edits,
        )
        mark_output_dirty()
        st.rerun()

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
