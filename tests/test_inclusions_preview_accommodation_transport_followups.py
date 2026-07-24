from tests.support.inclusion_contract import (
    build_inclusion_sections,
    inclusion_item_text,
    inclusion_item_texts,
    inclusion_section_text,
    inclusion_text,
)
import sys
import types

st_module = types.ModuleType("streamlit")
st_module.session_state = {}
st_module.warning = lambda *a, **k: None
st_module.success = lambda *a, **k: None
components_module = types.ModuleType("streamlit.components")
v1_module = types.ModuleType("streamlit.components.v1")
v1_module.declare_component = lambda *a, **k: (lambda **kwargs: None)
components_module.v1 = v1_module
st_module.components = components_module
sys.modules.setdefault("streamlit", st_module)
sys.modules.setdefault("streamlit.components", components_module)
sys.modules.setdefault("streamlit.components.v1", v1_module)

from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from generator import group_rows_by_day
from ui.inclusion_pages import render_categorized_inclusions_pages, render_inclusion_page_inner_htmls
from app_modules.itinerary_html import build_itinerary_html
from visual_editor_component.editor_workflow import apply_visual_editor_result


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_activity_inclusions_show_activity_date_and_detail_line_without_bullets():
    raw = """
	Day 2	Activity		02/10/2026						Copenhagen	Copenhagen: Secret Food Tours - Time: 11:30 am - 2:30 pm - Includes: Two types of local Smørrebrød, Danish meatballs, Flæskesteg - roasted pork with crispy crackling
"""
    rows = _rows(raw)
    sections = build_inclusion_sections(rows, group_rows_by_day(rows))
    activity_section = next(section for section in sections if section.title == "Activities & experiences")
    assert inclusion_item_texts(activity_section) == (
        "Copenhagen Food Tour - 2nd of October\nTwo types of local Smørrebrød, Danish meatballs, Flæskesteg - roasted pork with crispy crackling",
    )

    html = render_categorized_inclusions_pages("What’s included", sections)
    assert "Copenhagen Food Tour - 2nd of October" in html
    assert "inclusion-entry-detail" in html
    activities_slice = html.split("Activities &amp; experiences", 1)[1]
    assert "<ul" not in activities_slice.split('</div><div class="content-block', 1)[0]


def test_visual_preview_uses_same_inclusion_pagination_rule_as_pdf():
    sections = [
        {"title": "Accommodation", "items": ["Hotel One\n1 night. Breakfast included."]},
        {"title": "Activities & experiences", "items": [f"Activity {i} - 1st of June\nGuide, ticket, transfer" for i in range(1, 25)]},
        {"title": "Private transfers", "items": ["Private transfer from airport to hotel"]},
    ]
    page_htmls = render_inclusion_page_inner_htmls(sections)
    full_html = render_categorized_inclusions_pages("What’s included", sections)

    assert len(page_htmls) >= 2
    assert full_html.count('categorized-inclusions-page') == len(page_htmls)
    # Category splitting keeps whole categories together when they do not fit on the current page.
    assert "Private transfers" not in page_htmls[0]
    assert any("Private transfers" in page for page in page_htmls[1:])


def test_visual_editor_saved_inclusion_pages_render_as_multiple_pdf_pages():
    output_edits = {}
    result = {
        "final_pages": {
            "whats_included_pages_html": [
                {"html": '<div class="content-block inclusion-category-block"><div class="section-title">Accommodation</div><div>Hotel A</div></div>'},
                {"html": '<div class="content-block inclusion-category-block"><div class="section-title">Activities &amp; experiences</div><div>Activity B</div></div>'},
            ]
        }
    }
    assert apply_visual_editor_result(result, output_edits)
    html = build_itinerary_html([], {}, output_edits)
    assert html.count('categorized-inclusions-page') == 2
    assert "What’s included continued" not in html
    assert html.count("What’s included") >= 2


def test_hotel_bed_type_is_preserved_in_day_and_inclusions():
    raw = """
	Day 1	Hotel	1	09/07/2026	10/07/2026					Reykjavik	4 Star ,Hotel Reykjavík Grand , 1x Atrium View Double room ,full double bed, Incl Breakfast
"""
    rows = _rows(raw)
    hotel = rows[0]
    assert hotel["room_category"] == "1 x Atrium View Double Room - full double bed"

    html = build_itinerary_html(rows, group_rows_by_day(rows), {})
    assert "Room category: 1 x Atrium View Double Room - full double bed, breakfast included" in html
    assert "1 x Atrium View Double Room - full double bed. Breakfast included." in html


def test_transport_schedule_fallback_appears_for_overnight_train_and_coach_inclusions():
    raw = """
	Day 1	Transfer 	1	28/10/2026	29/10/2026					Helsinki 	Overnight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 11:13 pm - 10:59 am - 1  x  downstairs cabin for two people
	Day 2	Transfer 		31/10/2026						Kakslauttenen	Bus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Kakslauttenen Arctic Resort - 11:45 am - 3:02 pm - Tickets Included
"""
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    html = build_itinerary_html(rows, grouped, {})

    assert "Santa Claus Express to Rovaniemi" in html
    assert "11:13 PM - 10:59 AM" in html
    assert "1 x downstairs cabin for two people" in html
    assert "Panoramic Coach Transfer" in html
    assert "11:45 AM - 3:02 PM" in html
    assert "coach ticket included" in html.lower()
