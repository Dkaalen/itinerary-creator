from pathlib import Path

from tests.support.streamlit_stub import install_streamlit_stub

install_streamlit_stub()

from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.output_brand import BOOKNORDICS_BRAND
from app_modules.output_brand_cover import apply_output_brand_cover_palette
from app_modules.parse_workflow import parse_and_normalize_itinerary
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.cover_contrast import cover_text_area_is_dark
from itinerary_generation.cover_theme import get_cover_theme
from pdf_exporter_modules.image_layout import make_cover_cropped_image
from ui.output_edits import make_output_edit_state
from visual_editor_component import editor_payload_images


_DARK_SAMPLE = """Day 1\tArrival\t21.11.2026\t\tOslo: Welcome to Norway
Day 1\tHotel\t21.11.2026\t22.11.2026\tOslo: Check in to your accommodation for a 1 night stay - Thon Hotels Opera - Standard Room - Breakfast included
Day 2\tActivity\t22.11.2026\t\tOslo: Northern Lights Chase - Time: 6:00 pm - 11:00 pm - Includes: Guide
Day 3\tDeparture\t23.11.2026\t\tOslo: Departure home"""


_LIGHT_SAMPLE = """Day 1\tArrival\t21.07.2026\t\tOslo: Welcome to Norway
Day 1\tHotel\t21.07.2026\t22.07.2026\tOslo: Check in to your accommodation for a 1 night stay - Thon Hotels Opera - Standard Room - Breakfast included
Day 2\tDeparture\t22.07.2026\t\tOslo: Departure home"""


def _context_for(raw_text: str):
    rows = parse_and_normalize_itinerary(raw_text)
    grouped = group_rows_by_day(rows)
    edits = make_output_edit_state(rows, grouped)
    edits["output_brand"] = BOOKNORDICS_BRAND
    edits["color_preset"] = "Booknordics B2C"
    edits["pictures_added"] = True
    return build_itinerary_render_context(rows, grouped, edits)


def test_booknordics_cover_uses_light_text_on_dark_selected_image():
    context = _context_for(_DARK_SAMPLE)

    assert context.cover_theme["cover_text_mode"] == "light"
    assert context.cover_theme["ink"] == "#FAFAFB"
    assert context.cover_theme["muted"] == "#D7DDE5"
    assert context.cover_theme["accent"] == "#FF0041"
    assert context.render_document.cover.ink == "#FAFAFB"


def test_booknordics_cover_uses_navy_text_on_light_selected_image():
    context = _context_for(_LIGHT_SAMPLE)

    assert context.cover_theme["cover_text_mode"] == "dark"
    assert context.cover_theme["ink"] == "#00193C"
    assert context.cover_theme["muted"] == "#667085"


def test_cover_contrast_reads_actual_cropped_background_area():
    dark = Path("assets/cover_backgrounds/autumn_northern_lights.webp")
    light = Path("assets/cover_backgrounds/summer.webp")

    assert cover_text_area_is_dark(dark, "top") is True
    assert cover_text_area_is_dark(light, "top") is False


def test_booknordics_preview_and_editor_css_remove_cover_card():
    preview_css = Path("app_modules/preview_css_brand_booknordics.py").read_text(encoding="utf-8")
    editor_css = Path("visual_editor_component/frontend/styles/editor_brand_booknordics.css").read_text(encoding="utf-8")
    pdf_cover = Path("pdf_exporter_modules/cover_page.py").read_text(encoding="utf-8")

    assert "background: transparent" in preview_css
    assert "background: transparent" in editor_css
    assert "box-shadow: none" in preview_css
    assert "box-shadow: none" in editor_css
    assert "boxed_story_table(card_story" not in pdf_cover
    assert "_append_booknordics_cover_text" in pdf_cover


def test_option_previews_are_bounded_tiny_payloads_for_immediate_swap_preview(monkeypatch):
    calls = []

    def fake_preview(path, option=False):
        calls.append((path, option))
        return f"preview:{path}:{option}"

    monkeypatch.setattr(editor_payload_images, "get_image_preview_for_path", fake_preview)
    options = [{"path": f"/bank/image-{index}.jpg", "name": f"Image {index}"} for index in range(6)]

    enriched = editor_payload_images._with_option_previews(options, preview_limit=2)

    assert [item.get("preview_data_uri") for item in enriched[:2]] == [
        "preview:/bank/image-0.jpg:True",
        "preview:/bank/image-1.jpg:True",
    ]
    assert all("data_uri" not in item for item in enriched)
    assert [item["path"] for item in enriched[:2]] == ["/bank/image-0.jpg", "/bank/image-1.jpg"]
    assert calls == [("/bank/image-0.jpg", True), ("/bank/image-1.jpg", True)]


def test_pdf_image_variants_reuse_persistent_cache_across_temp_dirs(tmp_path, monkeypatch):
    from PIL import Image

    cache_root = tmp_path / "cache-root"
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(cache_root))
    source = tmp_path / "source.jpg"
    Image.new("RGB", (1200, 800), (20, 40, 80)).save(source)

    first_temp = tmp_path / "first"
    second_temp = tmp_path / "second"
    first_temp.mkdir()
    second_temp.mkdir()

    first = make_cover_cropped_image(source, 400, 240, first_temp, crop_focus="top")
    second = make_cover_cropped_image(source, 400, 240, second_temp, crop_focus="top")

    assert first and first.exists()
    assert second and second.exists()
    assert first.name == second.name
    assert (cache_root / "itinerary_pdf_image_cache" / first.name.removeprefix("day_image_")).exists()
