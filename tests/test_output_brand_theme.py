from pathlib import Path
from tests.support.static_contracts import read_contract_text

from tests.support.streamlit_stub import install_streamlit_stub

install_streamlit_stub()

from app_modules.itinerary_html import build_itinerary_html
from app_modules.output_brand import BOOKNORDICS_BRAND, AGENT_BRAND, is_booknordics, output_brand_id
from app_modules.parse_workflow import parse_and_normalize_itinerary
from app_modules.render_context_cover_data import build_cover_context_data
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.render_model import RenderDay
from ui.app_constants import COLOR_PRESETS
from ui.output_edits import make_output_edit_state
from visual_editor_component.editor_payload_builder import build_visual_editor_payload
from pdf_exporter_modules.pdf_branding import configure_pdf_brand
from pdf_exporter_modules.pdf_day_renderer import day_label


def _sample_rows_and_edits(output_brand=BOOKNORDICS_BRAND):
    raw_text = """Day 1\tArrival\t21.12.2026\t\tTromsø: Welcome to Norway
Day 1\tHotel\t21.12.2026\t22.12.2026\tTromsø: Check in to your accommodation for a 1 night stay - Quality Grand Tromso Hotel - 1 x Double room - Double bed - Breakfast included
Day 2\tDeparture\t22.12.2026\t\tTromsø: Departure home"""
    rows = parse_and_normalize_itinerary(raw_text)
    grouped_days = group_rows_by_day(rows)
    edits = make_output_edit_state(rows, grouped_days)
    edits["output_brand"] = output_brand
    edits["color_preset"] = "Booknordics B2C" if output_brand == BOOKNORDICS_BRAND else "Classic Agent"
    return rows, grouped_days, edits


def test_output_brand_defaults_to_agent():
    assert output_brand_id({}) == AGENT_BRAND
    assert not is_booknordics({})


def test_booknordics_palette_matches_brand_specification():
    colors = COLOR_PRESETS["Booknordics B2C"]
    assert colors["page_bg"] == "#FAFAFB"
    assert colors["ink"] == "#00193C"
    assert colors["accent"] == "#FF0041"


def test_cover_context_exposes_booknordics_brand_and_logo():
    data = build_cover_context_data([], {}, {"output_brand": BOOKNORDICS_BRAND, "color_preset": "Booknordics B2C"}, {})
    assert data["output_brand"] == BOOKNORDICS_BRAND
    assert data["brand_logo_data_uri"].startswith("data:image/png;base64,")
    assert data["colors"]["ink"] == "#00193C"


def test_booknordics_html_preview_embeds_brand_font_and_colors():
    rows, grouped_days, edits = _sample_rows_and_edits()
    html = build_itinerary_html(rows, grouped_days, edits)

    assert 'data-output-brand="booknordics_customer"' in html
    assert "@font-face" in html
    assert "DM Sans" in html
    assert "#00193C" in html
    assert "#FF0041" in html
    assert "Georgia, 'Times New Roman', serif" in html  # Agent fallback remains available, but brand overrides it.
    assert '<span class="day-kicker-symbol">•</span>' in html
    assert ".preview-background[data-output-brand=\"booknordics_customer\"] .day-image-slot" in html


def test_booknordics_day_labels_use_pdf_safe_separator():
    configure_pdf_brand(BOOKNORDICS_BRAND)
    try:
        label = day_label(RenderDay(day="Day 1", number="1", city="Tromsø", date="21st of December", title="Welcome", intro="Intro"))
    finally:
        configure_pdf_brand(AGENT_BRAND)

    assert label == "DAY 1 • TROMSØ • 21st of December"
    assert "✦" not in label


def test_visual_editor_payload_carries_booknordics_brand_contract():
    rows, grouped_days, edits = _sample_rows_and_edits()
    payload = build_visual_editor_payload(rows, grouped_days, edits)

    assert payload["brand"]["output_brand"] == BOOKNORDICS_BRAND
    assert payload["brand"]["colors"]["ink"] == "#00193C"
    assert payload["brand"]["colors"]["accent"] == "#FF0041"
    assert payload["brand"]["logo_data_uri"].startswith("data:image/png;base64,")
    assert "@font-face" in payload["brand"].get("font_face_css", "")


def test_visual_editor_frontend_has_booknordics_theme_and_safe_streamlit_bridge():
    brand_css = read_contract_text("visual_editor_component/frontend/styles/editor_brand_booknordics.css")
    render_js = read_contract_text("visual_editor_component/frontend/js/render.js")
    shell_js = read_contract_text("visual_editor_component/frontend/js/editor_shell.js")
    bridge_js = read_contract_text("visual_editor_component/frontend/js/streamlit_bridge.js")
    serialization_js = read_contract_text("visual_editor_component/frontend/js/serialization.js")

    assert 'data-output-brand="booknordics_customer"' in brand_css
    assert "font-family: \"DM Sans\", sans-serif" in brand_css
    assert "#FF0041" in brand_css
    assert "editorShellOpenHtml(brand)" in render_js
    assert "--brand-logo" in shell_js
    assert "data-editor-brand-fonts" in shell_js
    assert "let streamlitBridgeRenderReceived = false" in bridge_js
    assert "if (!streamlitBridgeRenderReceived) return" in bridge_js
    assert "delete full.brand" in serialization_js
