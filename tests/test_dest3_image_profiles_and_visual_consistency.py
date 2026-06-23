from __future__ import annotations

from pathlib import Path

from PIL import Image
from reportlab.platypus import Table

from images.matcher import select_day_image
from images.matcher_context import build_day_context
from itinerary_generation.transport_domain.render import build_travel_arrangements_render_block
from pdf_exporter_modules.styles import make_styles
from pdf_exporter_modules.typed_exporter import _render_premium_travel_block_story


def _save_jpg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (48, 32), (80, 120, 140)).save(path, format="JPEG")


def test_day_context_exposes_registry_image_profiles():
    context = build_day_context(
        "Day 1",
        [
            {
                "day": "Day 1",
                "date": "15.09.2026",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Bergen",
                "title": "Bergen harbour walk",
                "details": "Explore the harbour and waterfront.",
            }
        ],
    )

    assert "southern_coastal" in context["image_profiles"]
    assert "southern_coastal" in context["season_profiles"]


def test_registry_image_profile_bonus_prefers_mountain_resort_visuals(tmp_path):
    bank = tmp_path / "image_bank"
    city_dir = bank / "Sweden" / "Åre"
    _save_jpg(city_dir / "Are_City_Street_Summer.jpg")
    _save_jpg(city_dir / "Are_Winter_Ski_Mountain_Resort.jpg")

    rows = [
        {
            "day": "Day 1",
            "date": "15.12.2026",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Åre",
            "title": "Check in to your accommodation",
            "details": "Åre: Check in to your accommodation for a 2 night stay",
        }
    ]

    match = select_day_image("Day 1", rows, bank)

    assert match is not None
    assert Path(match["path"]).name == "Are_Winter_Ski_Mountain_Resort.jpg"
    assert "destination image profile" in match["reason"]


def test_premium_travel_modules_use_native_proposal_style_not_floating_cards():
    preview_css = Path("app_modules/itinerary_html_styles.py").read_text(encoding="utf-8")
    editor_css = Path("visual_editor_component/frontend/styles/editor.css").read_text(encoding="utf-8")

    for css in (preview_css, editor_css):
        assert "background: transparent" in css
        assert "border-radius: 0" in css
        assert "box-shadow: none" in css
        assert "grid-template-columns: 82px 1fr" in css


def test_typed_pdf_premium_travel_module_is_not_boxed_table():
    rows = [
        {
            "type": "Cruise",
            "effective_type": "Cruise",
            "city": "Stavanger",
            "title": "Atlantic Coastal Cruise Transfer to Bergen",
            "details": "Stavanger: Atlantic Coastal Cruise Transfer to Bergen - Time: 07:30 am - 1:00 pm - Meeting point: Stavanger Cruise Port - Includes: Tickets, Fjord Lounge",
            "time": "07:30 am - 1:00 pm",
            "includes": ["Tickets", "Fjord Lounge"],
        }
    ]
    block = build_travel_arrangements_render_block(rows)

    story = _render_premium_travel_block_story(block, make_styles())

    assert story
    assert not any(isinstance(flowable, Table) for flowable in story)
