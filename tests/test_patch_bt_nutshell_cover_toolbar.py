from __future__ import annotations

import json
from pathlib import Path

from app_modules.itinerary_html import build_itinerary_html
from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.common import group_rows_by_day
from normalizer import normalize_itinerary_rows
from parser_modules.parser_main import parse_itinerary
from visual_editor_component.editor_payload_builder import build_visual_editor_payload
from visual_editor_component.editor_result_applier import apply_visual_editor_result


SAMPLE_INPUT = """
Day 1	Arrival	28.11.2026		Oslo: Welcome to Norway
Day 1	Hotel	28.11.2026	29.11.2026	Oslo: Check in to your accommodation for a 1 night stay - Radisson Blu Plaza Hotel - Standard Double room - Breakfast included
Day 2	Activity	29.11.2026		Oslo: Norway in a Nutshell to Flåm - Time: 08:25 am - 2:05 pm - Meeting point: Oslo Central Station - Includes:  Train transfer Oslo to Myrdal, Train tranfser Myrdal to Flåm
Day 3	Activity	30.11.2026		Flåm: Norway in a Nutshell to Bergen - Time: 09:30 am - 2:15 pm - Meeting point: Flåm Harbor - Includes: Fjord Cruise Flåm to Gudvangen, Coach Transfer Gudvangen to Voss, Train transfer Voss to Bergen
Day 4	Activity	01.12.2026		Bergen: Tickets to Fløybanen Funicular - Time: Flexible - Meeting point: Fløybanene - Includes: Tickets - Description: Take the funicular Fløibanen to the top of Mount Fløyen and experience spectacular views of the city, the fjord and the surrounding mountains.
Day 7	Activity	04.12.2026		Tromsø: Fjord Tour of Kvaløya & Sommarøy incl. Lunch - Time: 10:00 am - 3:30 pm - Meeting point: Hotel Pick up - Includes: Pick-up/drop-off in central Tromsø, Knowledgeable, multilingual guide, Free photographs from the trip, 2-course meal with coffee or tea - Description: On this tour we will travel in our minibus around the fjords of the island of Kvaløya, nearby Tromsø, and enjoy a nice lunch on Sommarøy island.
"""


def _rows_and_grouped():
    rows = normalize_itinerary_rows(parse_itinerary(SAMPLE_INPUT))
    return rows, group_rows_by_day(rows)


def test_patch_bt_norway_nutshell_titles_preserve_supplier_destination() -> None:
    rows, grouped = _rows_and_grouped()
    nutshell_titles = [row["title"] for row in rows if "Norway in a Nutshell" in row.get("title", "")]

    assert "Norway in a Nutshell to Flåm" in nutshell_titles
    assert "Norway in a Nutshell to Bergen" in nutshell_titles
    assert "Norway in a Nutshell to Myrdal" not in nutshell_titles
    assert "Norway in a Nutshell to Gudvangen" not in nutshell_titles

    render_titles = {day.day: day.title for day in build_itinerary_render_context(rows, grouped, {}).render_document.days}
    assert render_titles["Day 2"] == "Norway in a Nutshell to Flåm"
    assert render_titles["Day 3"] == "Norway in a Nutshell to Bergen"


def test_patch_bt_norway_nutshell_supplier_legs_are_rendered() -> None:
    rows, grouped = _rows_and_grouped()
    context = build_itinerary_render_context(rows, grouped, {})
    rendered_bits = []
    for day in context.render_document.days:
        for block in day.blocks:
            rendered_bits.extend(block.lines)
            for section in block.extra_sections:
                rendered_bits.extend(section.items)
    rendered_text = "\n".join(rendered_bits)

    assert "Oslo → Myrdal" in rendered_text or "Train transfer Oslo to Myrdal" in rendered_text
    assert "Myrdal → Flåm" in rendered_text or "Train transfer Myrdal to Flåm" in rendered_text
    assert "Flåm → Gudvangen" in rendered_text or "Fjord Cruise Flåm to Gudvangen" in rendered_text
    assert "Gudvangen → Voss" in rendered_text or "Coach Transfer Gudvangen to Voss" in rendered_text
    assert "Voss → Bergen" in rendered_text or "Train transfer Voss to Bergen" in rendered_text
    assert "Bergen Railway, Flåm Railway, Fjord cruise, Scenic bus journey" not in rendered_text


def test_patch_bt_strong_supplier_activity_titles_and_floibanen_wording() -> None:
    rows, grouped = _rows_and_grouped()
    context = build_itinerary_render_context(rows, grouped, {})
    activity_blocks = [block for day in context.render_document.days for block in day.blocks if block.kind == "activity"]
    titles = [block.title for block in activity_blocks]
    descriptions = "\n".join(block.description for block in activity_blocks)

    assert "Fjord Tour of Kvaløya & Sommarøy incl. Lunch" in titles
    assert "Photo Tour to Arctic Landscapes and Fjords" not in titles
    assert "Mount Fløyen" in descriptions
    assert "Mount Fløibanen" not in descriptions


def test_patch_bt_cover_and_summary_images_share_preview_pdf_state() -> None:
    rows, grouped = _rows_and_grouped()
    output_edits = {"pictures_added": True}
    context = build_itinerary_render_context(rows, grouped, output_edits)

    assert context.cover_background_path
    assert context.summary_background_path
    assert context.render_document.cover.background_path == context.cover_background_path
    assert context.render_document.summary.background_path == context.summary_background_path

    html = build_itinerary_html(rows, grouped, output_edits)
    assert 'data-cover-background-path' in html
    assert 'summary-page' in html
    assert context.summary_background_path in html

    payload = build_visual_editor_payload(rows, grouped, output_edits)
    assert payload["cover"]["cover_image"]["path"]
    assert payload["cover"]["summary_image"]["path"]
    assert payload["cover"]["cover_image"]["data_uri"].startswith("data:image/")
    assert payload["cover"]["summary_image"]["data_uri"].startswith("data:image/")
    assert payload["cover"]["cover_image"]["options"]
    assert payload["cover"]["summary_image"]["options"]


def test_patch_bt_cover_image_edits_are_persisted(monkeypatch) -> None:
    monkeypatch.setitem(__import__("streamlit").session_state, "_visual_editor_current_source_signature", "")
    output_edits = {"pictures_added": True}
    payload = {
        "cover": {
            "cover_image": {"mode": "none", "path": "/tmp/ignored.jpg", "crop_focus": "bottom"},
            "summary_image": {"mode": "manual", "path": "assets/cover_backgrounds/winter.webp", "crop_focus": "center"},
        },
        "workflow": {"pictures_added": True},
    }

    assert apply_visual_editor_result(json.dumps(payload), output_edits)
    assert output_edits["cover_image"] == {"mode": "none", "path": "", "crop_focus": "bottom"}
    assert output_edits["summary_image"] == {"mode": "manual", "path": "assets/cover_backgrounds/winter.webp", "crop_focus": "center"}


def test_patch_bt_text_formatting_sidebar_is_visible_and_wired() -> None:
    render_js = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")
    inspector_js = Path("visual_editor_component/frontend/js/editor_inspector.js").read_text(encoding="utf-8")
    serialization_js = Path("visual_editor_component/frontend/js/serialization.js").read_text(encoding="utf-8")

    advanced_position = render_js.index('class="advanced-tools"')
    pages_position = render_js.index('class="pages-menu"')
    assert pages_position < advanced_position
    assert "inspectorFontFamilyPreset')?.addEventListener" in inspector_js
    assert "inspectorFontSizePreset')?.addEventListener" in inspector_js
    assert "applyFontFamilyPreset" in inspector_js
    assert "applyFontSizePreset" in inspector_js
    assert "applyColorPreset" in inspector_js
    assert "cover_image" in serialization_js
    assert "summary_image" in serialization_js
