from __future__ import annotations

from pathlib import Path

from PIL import Image
from reportlab.platypus import Table

from images.matcher import select_day_image
from images.matcher_context import build_day_context
from itinerary_generation.transport_domain.render import build_travel_arrangements_render_block
from pdf_exporter_modules.styles import make_styles
from pdf_exporter_modules.typed_exporter import _block_story


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


def test_special_travel_modules_use_native_proposal_rendering():
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

    assert block.css_class == "travel-sequence-block"
    assert "premium-travel-card" not in block.css_class
    assert block.lines == []


def test_typed_pdf_special_travel_module_uses_native_block_story():
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

    story = _block_story(block, make_styles())

    assert story
    assert not any(isinstance(flowable, Table) for flowable in story)
