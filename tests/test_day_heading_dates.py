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
