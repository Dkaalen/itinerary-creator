from __future__ import annotations

from pathlib import Path
import sys
import types

streamlit_stub = types.SimpleNamespace(
    error=lambda *args, **kwargs: None,
    warning=lambda *args, **kwargs: None,
    success=lambda *args, **kwargs: None,
    info=lambda *args, **kwargs: None,
    session_state={},
)
sys.modules.setdefault("streamlit", streamlit_stub)

from app_modules.workflow_actions import enter_picture_stage
from images.day_image_selection import select_day_images_with_overrides
from itinerary_generation.cover_route import create_cover_route_line
from itinerary_generation.day_grouping import group_rows_by_day
from itinerary_generation.day_planner import plan_day
from itinerary_generation.editable_draft import mirror_draft_to_legacy_output_edits, normalise_editable_draft
from normalizer_modules.core import normalize_itinerary_rows
from parser_modules.parser_main import parse_itinerary


def _parse_normalized(raw: str) -> list[dict]:
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_visual_editor_stale_picture_workflow_false_cannot_reset_active_picture_state():
    output_edits = {"pictures_added": True}
    draft = normalise_editable_draft({"workflow": {"pictures_added": False}})

    mirror_draft_to_legacy_output_edits(output_edits, draft)

    assert output_edits["pictures_added"] is True


def test_enter_picture_stage_does_not_report_success_when_no_images_match():
    state = {
        "output_edits": {"days": {}},
        "parsed_rows": [{"day": "Day 1", "city": "Oslo", "type": "Activity", "effective_type": "Activity", "title": "Walking tour"}],
        "grouped_days": {"Day 1": [{"day": "Day 1", "city": "Oslo", "type": "Activity", "effective_type": "Activity", "title": "Walking tour"}]},
        "itinerary_html": "<html></html>",
    }

    result = enter_picture_stage(
        state,
        status_func=lambda: {"full_bank_found": True, "using_full_destination_bank": True},
        connect_func=lambda: {"full_bank_found": True, "using_full_destination_bank": True},
        select_images_func=lambda grouped, edits: {day: None for day in grouped},
        audit_images_func=lambda grouped, matches, edits: [],
        rebuild_preview_func=lambda **kwargs: True,
    )

    assert result.ok is False
    assert "no destination pictures matched" in result.message.lower()
    assert state["output_edits"]["pictures_added"] is False
    assert state["app_stage"] == "edit"


def test_day_image_selection_normalizes_destination_aliases_for_full_image_bank(tmp_path):
    bank = tmp_path / "image_bank_full"
    for destination in ["Oslo", "Flåm", "Bergen", "Tromsø"]:
        path = bank / "Norway" / destination / f"{destination}_winter.webp"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not-a-real-image-but-scannable")

    grouped = {
        "Day 1": [{"day": "Day 1", "city": "Oslo", "type": "Activity", "effective_type": "Activity", "title": "Oslo walking tour"}],
        "Day 2": [{"day": "Day 2", "city": "Flam", "type": "Hotel", "effective_type": "Hotel", "title": "Flåmsbrygga Hotell"}],
        "Day 3": [{"day": "Day 3", "city": "Bergen", "type": "Activity", "effective_type": "Activity", "title": "Bergen walking tour"}],
        "Day 4": [{"day": "Day 4", "city": "Tromso", "type": "Activity", "effective_type": "Activity", "title": "Tromsø fjord tour"}],
    }

    matches = select_day_images_with_overrides(grouped, {}, app_root=tmp_path, image_bank_scan_paths=[bank])

    assert all(matches[day] and matches[day]["path"] for day in grouped)
    assert "Flåm" in matches["Day 2"]["path"]
    assert "Tromsø" in matches["Day 4"]["path"]


def test_hotel_looking_transfer_row_counts_as_bergen_overnight_destination():
    raw = """Day 1\tHotel\t\t01/10/2026\t03/10/2026\t\t\t\t\tOslo\t3 Star ,Comfort Hotel Børsparken ,, 2xNight , Superior Double room , Ful double bed , Incl Brekafast
Day 3\tHotel\t\t03/10/2026\t04/10/2026\t\t\t\t\tFlam\t3 Star,Flåmsbrygga Hotell , 1xNight , 1xStandard Family  Room, Incl Brekafast
Day 4\tActivity\t\t04/10/2026\t\t\t\t\t\tBergen\tFLam : Flåm to Bergen: Norway in a Nutshell Part 2
Day 4\tTransfer \t\t04/10/2026\t06/10/2026\t\t\t\t\tBergen\t3 Star,Scandic Byparken , 2xNight , 1xStandard Family  Room, Incl Brekafast
Day 6\tHotel\t\t06/10/2026\t08/10/2026\t\t\t\t\tTromso\t3 Star ,Thon Hotel Polar, , 2xNight , 1xStandard Family  Room, Incl Brekafast
"""

    rows = _parse_normalized(raw)
    day4_hotel = next(row for row in rows if row["day"] == "Day 4" and "Scandic Byparken" in row.get("title", ""))

    assert day4_hotel["effective_type"] == "Hotel"
    assert create_cover_route_line(rows) == "Oslo · Flåm · Bergen · Tromsø"


def test_igloo_transfer_day_uses_accommodation_title_and_preserves_aurora_nest_room():
    raw = """Day 6\tTransfer \t19/12/2026\t\t\t\t\t\t\tRovaniemi\tPrivate Transfer to Glass Igloo Stay
Day 6\tHotel\t19/12/2026\t20/12/2026\t\t\t\t\t\tRovaniemi\tAito Igloo & Spa Resort , 1xngiht , 2xAurora Nest ( Similar to Igloo ) , incl breakfast
"""

    rows = _parse_normalized(raw)
    grouped = group_rows_by_day(rows)
    hotel = next(row for row in rows if row.get("effective_type") == "Hotel")
    day_plan = plan_day(grouped["Day 6"])

    assert day_plan.title == "Aito Igloo & Spa Resort Stay"
    assert "Welcome to Rovaniemi" not in day_plan.title
    assert hotel["hotel_nights"] == "1"
    assert "Aurora Nest" in hotel["room_category"]
    assert "Northern Lights Next" not in hotel["room_category"]
