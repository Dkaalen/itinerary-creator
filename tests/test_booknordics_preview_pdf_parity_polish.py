from pathlib import Path
from tests.support.static_contracts import read_contract_text

from tests.support.streamlit_stub import install_streamlit_stub

install_streamlit_stub()

from app_modules.itinerary_html import build_itinerary_html
from app_modules.output_brand import BOOKNORDICS_BRAND
from app_modules.parse_workflow import parse_and_normalize_itinerary
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.client_sanitizer import contains_price_or_currency, sanitize_client_text
from itinerary_generation.render_model import RenderFinalPage, RenderFinalSection
from itinerary_generation.structured_model import StructuredListItem, StructuredListSection
from itinerary_generation.transport_domain.inclusions import transport_line
from ui.app_constants import DEFAULT_IMPORTANT_TRAVEL_NOTES
from ui.final_pages import get_important_travel_notes
from ui.inclusion_pages import paginate_categorized_inclusions, render_categorized_inclusions_pages
from ui.output_edits import make_output_edit_state


_SAMPLE = """Day 1\tArrival\t21.12.2026\t\tTromsø: Welcome to Norway
Day 1\tHotel\t21.12.2026\t22.12.2026\tTromsø: Check in to your accommodation for a 1 night stay - Quality Grand Tromso Hotel - 1 x Double room - Double bed - Breakfast included
Day 2\tDeparture\t22.12.2026\t\tTromsø: Departure home"""


def test_visual_editor_booknordics_backgrounds_do_not_tile_selected_images():
    brand_css = read_contract_text("visual_editor_component/frontend/styles/editor_brand_booknordics.css")
    render_js = read_contract_text("visual_editor_component/frontend/js/render.js")
    summary_js = read_contract_text("visual_editor_component/frontend/js/editor_render_summary.js")

    assert "background-color: var(--paper, #FAFAFB)" in brand_css
    assert "background: var(--paper, #FAFAFB);" not in brand_css
    assert "background-size: cover !important" in brand_css
    assert "background-repeat: no-repeat !important" in brand_css
    assert "background-size: cover; background-repeat: no-repeat" in render_js
    assert "background-size: cover, cover" in summary_js
    assert "background-repeat: no-repeat, no-repeat" in summary_js


def test_booknordics_day_page_sublabels_are_not_all_red():
    brand_css = read_contract_text("visual_editor_component/frontend/styles/editor_brand_booknordics.css")
    preview_css = read_contract_text("app_modules/preview_css_brand_booknordics.py")

    assert '.day-page .section-title' in brand_css
    assert '-webkit-text-fill-color: var(--ink, #00193C)' in brand_css
    assert '.day-page .section-title' in preview_css
    assert 'color: var(--ink);' in preview_css


def test_generated_booknordics_preview_uses_fitted_cover_and_continuation_titles():
    rows = parse_and_normalize_itinerary(_SAMPLE)
    grouped_days = group_rows_by_day(rows)
    edits = make_output_edit_state(rows, grouped_days)
    edits["output_brand"] = BOOKNORDICS_BRAND
    edits["color_preset"] = "Booknordics B2C"

    html = build_itinerary_html(rows, grouped_days, edits)

    assert 'data-output-brand="booknordics_customer"' in html
    assert "background-size: cover; background-repeat: no-repeat" in html
    assert "background-size: cover, cover; background-repeat: no-repeat, no-repeat" in html


def test_inclusion_pagination_balances_activities_with_transport_on_second_page():
    accommodation = [
        StructuredListItem(f"Hotel {index}", ("4 nights. Family room. Breakfast included.",))
        for index in range(4)
    ]
    activities = [
        StructuredListItem(
            f"Activity {index}",
            ("Scenic transfers, knowledgeable English-speaking guide, photography support, warm drinks, meal, small-group experience with maximum guests, scenic route details around fjords and beaches, plus photography instructions and warm snacks.",),
        )
        for index in range(11)
    ]
    flights = [
        StructuredListItem(
            "Flight from Tromsø to Svolvær",
            ("5:15 PM - 6:10 PM", "Flight tickets, 1 x 23 kg checked bag, 1 x 8 kg carry-on bag per person."),
        ),
        StructuredListItem(
            "Flight from Kiruna to Stockholm",
            ("2:15 PM - 3:55 PM", "Flight tickets, 1 x 23 kg checked bag, 1 x 8 kg carry-on bag per person."),
        ),
    ]
    rail = [StructuredListItem("Scenic Train Transfer from Narvik to Kiruna", ("3:00 PM - 5:53 PM", "Tickets."))]

    pages = paginate_categorized_inclusions([
        StructuredListSection("accommodation", "Accommodation", tuple(accommodation)),
        StructuredListSection("activities", "Activities & experiences", tuple(activities)),
        StructuredListSection("flights", "Flights", tuple(flights)),
        StructuredListSection("rail", "Rail journeys", tuple(rail)),
    ])

    assert len(pages) == 2
    assert [section["title"] for section in pages[0]] == ["Accommodation", "Activities & experiences"]
    assert [section["title"] for section in pages[1]] == ["Activities & experiences", "Flights", "Rail journeys"]
    assert len(pages[0][1]["items"]) < len(activities)


def test_important_notes_refresh_legacy_defaults_and_include_independent_transfers():
    legacy_defaults = DEFAULT_IMPORTANT_TRAVEL_NOTES[:-1]

    notes = get_important_travel_notes({"important_travel_notes_text": "\n".join(legacy_defaults)})

    assert notes == DEFAULT_IMPORTANT_TRAVEL_NOTES
    assert any("self-arranged" in note and "meeting points" in note for note in notes)


def test_client_sanitizer_preserves_baggage_per_person_but_still_removes_prices():
    baggage_allowance = "Flight tickets, 1 x 23 kg checked bag, 1 x 8 kg carry-on bag per person."

    assert sanitize_client_text(baggage_allowance) == baggage_allowance
    assert not contains_price_or_currency(baggage_allowance)
    assert not contains_price_or_currency(
        "Flight ticket, one checked bag up to 23 kg and one carry-on bag up to 8 kg per person."
    )
    assert sanitize_client_text("Optional entrance fee EUR 50 per person.") == "Optional entrance fee."
    assert contains_price_or_currency("Optional entrance EUR 50 per person.")
    assert contains_price_or_currency("Optional entrance 50 per person.")
    assert contains_price_or_currency("Checked bag fee 50 per person.")
    assert sanitize_client_text("Ticket EUR 50 per person, includes 1 x 23 kg checked bag per person.") == (
        "Ticket, includes 1 x 23 kg checked bag per person."
    )


def test_flight_final_inclusion_uses_client_ready_baggage_without_duplicate_raw_text():
    row = {
        "type": "Flight",
        "effective_type": "Flight",
        "city": "Tromsø",
        "title": "Flight to Svolvær",
        "time": "5:15 pm - 6:10 pm",
        "details": "Tromsø: Flight to Svolvær - Time: 5:15 pm - 6:10 pm - Luggage included: 1 x 23 kg check in and 1 x 8 kg carry on per person",
        "luggage_included": "1 x 23 kg check in and 1 x 8 kg carry on per person",
        "includes": ["1 x 23 kg check in and 1 x 8 kg carry on per person"],
    }

    line = transport_line(row)

    assert "1 x 23 kg check in" not in line
    assert "Flight tickets, 1 x 23 kg checked bag, 1 x 8 kg carry-on bag per person" in line


def test_final_section_titles_stay_clean_across_preview_and_pdf_contract():
    from app_modules.render_final_sections_html import render_final_section_html
    from pdf_exporter_modules.pdf_final_section_renderer import render_final_page

    section = RenderFinalSection(
        "whats_included",
        "What’s included",
        pages=[RenderFinalPage(items=["One"]), RenderFinalPage(items=["Two"])],
    )

    html = render_final_section_html(section)
    assert "What’s included continued" not in html
    assert html.count("What’s included") == 2

    categorized_html = render_categorized_inclusions_pages(
        "What’s included",
        [
            StructuredListSection(
                "activities",
                "Activities & experiences",
                tuple(StructuredListItem(f"Activity {index}", ("Long included detail text " * 10,)) for index in range(18)),
            )
        ],
    )
    assert "What’s included continued" not in categorized_html
    assert 'add_paragraph(story, title, styles["page_title"])' in Path(
        "pdf_exporter_modules/pdf_final_section_renderer.py"
    ).read_text(encoding="utf-8")
