from app_modules.output_brand import BOOKNORDICS_BRAND, AGENT_BRAND, is_booknordics, output_brand_id
from app_modules.render_context_cover_data import build_cover_context_data
from ui.app_constants import COLOR_PRESETS


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
