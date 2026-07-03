from __future__ import annotations



def test_group_tour_pickup_time_helper_has_single_owner() -> None:
    from pathlib import Path

    text_helpers = Path("itinerary_generation/group_tour_text.py").read_text(encoding="utf-8")
    master_rows = Path("itinerary_generation/group_tour_master_rows.py").read_text(encoding="utf-8")

    assert "def _package_pickup_time" not in text_helpers
    assert master_rows.count("def _package_pickup_time") == 1
    assert "_TIME_FIELD_RE" not in text_helpers
