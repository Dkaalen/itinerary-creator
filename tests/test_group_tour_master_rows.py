from __future__ import annotations

from pathlib import Path

from tests.support.static_contracts import read_contract_text


ROOT = Path(__file__).resolve().parents[1]


def test_group_tour_pickup_time_helper_has_single_neutral_owner() -> None:
    text_helpers = read_contract_text("itinerary_domain/group_tour_text.py")
    master_rows = read_contract_text("itinerary_domain/group_tour_master_rows.py")

    assert "def _package_pickup_time" not in text_helpers
    assert master_rows.count("def _package_pickup_time") == 1
    assert "_TIME_FIELD_RE" not in text_helpers
    assert not (ROOT / "itinerary_generation" / "group_tour_master_rows.py").exists()
