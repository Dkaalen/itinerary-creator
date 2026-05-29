from ui.day_pages import render_day_section


def test_day_heading_includes_day_date_when_available():
    rows = [
        {
            "row_id": "arrival-1",
            "day": "Day 1",
            "type": "Arrival",
            "effective_type": "Arrival",
            "city": "Bergen",
            "title": "Arrival in Bergen",
            "details": "Arrival in Bergen",
            "start_date": "2026-01-01",
            "end_date": "",
            "includes": [],
        }
    ]

    html = render_day_section("Day 1", rows, output_edits={})

    assert "DAY 1" in html
    assert "BERGEN" in html
    assert "1st of January" in html


def test_cover_includes_trip_date_range_and_groups_final_route_pair():
    from app_modules.itinerary_html import build_itinerary_html
    from generator import group_rows_by_day

    rows = [
        {
            "row_id": "arrival-1",
            "day": "Day 1",
            "type": "Arrival",
            "effective_type": "Arrival",
            "city": "Helsinki",
            "title": "Arrival in Helsinki",
            "details": "Arrival in Helsinki",
            "start_date": "2026-10-27",
            "end_date": "",
            "includes": [],
        },
        {
            "row_id": "departure-11",
            "day": "Day 11",
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Oslo",
            "title": "Private Hotel to Airport",
            "details": "Private Hotel to Airport",
            "start_date": "2026-11-06",
            "end_date": "",
            "includes": [],
        },
    ]

    html = build_itinerary_html(rows, group_rows_by_day(rows), output_edits={})

    assert '<div class="cover-dates">27th of October - 6th of November</div>' in html
    assert '<span class="cover-destination-pair">Helsinki&nbsp;·&nbsp;Oslo</span>' in html


def test_pdf_day_kicker_uses_selected_accent_color():
    from reportlab.lib import colors
    from pdf_exporter_modules.styles import apply_pdf_palette, make_styles

    apply_pdf_palette({"accent": "#F2055C"})
    styles = make_styles()

    assert styles["day_kicker"].textColor == colors.HexColor("#F2055C")
