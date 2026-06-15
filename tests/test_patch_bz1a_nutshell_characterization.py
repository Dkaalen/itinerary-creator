"""Characterization gates for the Norway in a Nutshell domain migration.

Patch BZ1A intentionally does not change production behavior. These tests lock
in source fidelity, product identity, route order, commercial metadata, and the
known renderer divergence that BZ1B/BZ1C must remove.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from itinerary_generation.day_grouping import group_rows_by_day
from itinerary_generation.titles import create_client_activity_title
from itinerary_generation.transport import get_transport_route_phrase
from itinerary_generation.transport_norway import (
    extract_norway_nutshell_route_legs,
    extract_norway_nutshell_route_points,
    extract_norway_nutshell_supplier_includes,
)
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.day_blocks import build_day_blocks


_REAL_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "real_inputs"
    / "scandinavia_cruise_premium_working.txt"
)


def _real_rows() -> list[dict]:
    return normalize_itinerary_rows(parse_itinerary(_REAL_FIXTURE.read_text(encoding="utf-8")))


def _real_nutshell_row(rows: list[dict]) -> dict:
    return next(
        row
        for row in rows
        if (row.get("activity_product") or {}).get("canonical_family") == "norway_in_a_nutshell"
    )


def test_bz1a_real_product_identity_route_and_commercial_status_are_preserved() -> None:
    rows = _real_rows()
    nutshell = _real_nutshell_row(rows)

    assert nutshell["type"] == "Activity"
    assert nutshell["effective_type"] == "Train"
    assert nutshell["commercial_status"] == "included"
    assert nutshell["commercial_reason"] == "default_included"
    assert nutshell["time"] == "8:00 AM - 8:00 PM"
    assert nutshell["activity_product"]["canonical_family"] == "norway_in_a_nutshell"
    assert nutshell["activity_product"]["product_type"] == "scenic_route"
    assert create_client_activity_title(nutshell) == "Norway in a Nutshell from Bergen to Oslo"
    assert get_transport_route_phrase(nutshell) == "Norway in a Nutshell from Bergen to Oslo"


def test_bz1a_real_product_keeps_adjacent_transfers_as_separate_ordered_rows() -> None:
    grouped = group_rows_by_day(_real_rows())
    day_rows = grouped["Day 16"]
    nutshell_index = next(
        index
        for index, row in enumerate(day_rows)
        if (row.get("activity_product") or {}).get("canonical_family") == "norway_in_a_nutshell"
    )

    assert day_rows[nutshell_index - 1]["title"] == "Private transfer to Bergen Central Station"
    assert day_rows[nutshell_index + 1]["title"] == "Private transfer to your accommodation"
    assert sum(
        (row.get("activity_product") or {}).get("canonical_family") == "norway_in_a_nutshell"
        for row in day_rows
    ) == 1


def test_bz1a_supplier_inclusions_keep_compound_leg_order() -> None:
    nutshell = _real_nutshell_row(_real_rows())
    supplier_legs = extract_norway_nutshell_supplier_includes(nutshell)

    assert supplier_legs[:5] == [
        "E-tickets for Voss railway: Bergen to Oslo",
        "E-tickets for bus: Voss to Gudvangen",
        "E-tickets for Fjord Cruise: Gudvangen to Flåm",
        "E-tickets for Flåm railway: Flåm to Myrdal",
        "E-tickets for Bergen railway: Myrdal to Oslo",
    ]
    assert "Luggage transfer" in nutshell["includes"]


def test_bz1a_oslo_to_bergen_timetable_preserves_order_modes_and_times() -> None:
    source = """Norway in a Nutshell from Oslo to Bergen
09:18 Oslo - 14:20 Myrdal via Train
14:41 Myrdal - 15:39 Flåm via Train
17:30 Flåm - 19:20 Gudvangen via Cruise
19:40 Gudvangen - 20:40 Voss via Scenic Bus
21:02 Voss - 22:15 Bergen via Train"""

    assert extract_norway_nutshell_route_points(source) == [
        "Oslo",
        "Myrdal",
        "Flåm",
        "Gudvangen",
        "Voss",
        "Bergen",
    ]
    assert extract_norway_nutshell_route_legs(source) == [
        {"departure_time": "9:18 AM", "origin": "Oslo", "arrival_time": "2:20 PM", "destination": "Myrdal", "mode": "Train"},
        {"departure_time": "2:41 PM", "origin": "Myrdal", "arrival_time": "3:39 PM", "destination": "Flåm", "mode": "Train"},
        {"departure_time": "5:30 PM", "origin": "Flåm", "arrival_time": "7:20 PM", "destination": "Gudvangen", "mode": "Cruise"},
        {"departure_time": "7:40 PM", "origin": "Gudvangen", "arrival_time": "8:40 PM", "destination": "Voss", "mode": "Scenic Bus"},
        {"departure_time": "9:02 PM", "origin": "Voss", "arrival_time": "10:15 PM", "destination": "Bergen", "mode": "Train"},
    ]


def test_bz1a_partial_route_preserves_known_points_without_inventing_times() -> None:
    source = (
        "Norway in a Nutshell from Oslo to Bergen - Includes: "
        "Train Oslo to Myrdal, Flåm Railway Myrdal to Flåm, "
        "Fjord Cruise Flåm to Gudvangen, Coach Gudvangen to Voss, "
        "Train Voss to Bergen"
    )

    assert extract_norway_nutshell_route_points(source) == [
        "Oslo",
        "Myrdal",
        "Flåm",
        "Gudvangen",
        "Voss",
        "Bergen",
    ]
    assert extract_norway_nutshell_route_legs(source) == []


@pytest.mark.parametrize(
    ("row_type", "suffix", "expected_status", "expected_reason"),
    [
        ("Optional", "", "optional", "explicit_optional"),
        ("Activity", " - Cost Not Included", "self_arranged", "cost_not_included"),
    ],
)
def test_bz1a_commercial_status_survives_product_normalization(
    row_type: str,
    suffix: str,
    expected_status: str,
    expected_reason: str,
) -> None:
    raw = (
        f"Day 1\t{row_type}\t01/09/2026\t\tOslo\t"
        "Norway in a Nutshell from Oslo to Bergen - "
        f"Includes: Train Oslo to Myrdal{suffix}"
    )
    row = normalize_itinerary_rows(parse_itinerary(raw))[0]

    assert row["activity_product"]["canonical_family"] == "norway_in_a_nutshell"
    assert row["commercial_status"] == expected_status
    assert row["commercial_reason"] == expected_reason


def test_bz1a_day_renderer_uses_canonical_nutshell_title() -> None:
    grouped = group_rows_by_day(_real_rows())
    day_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 16"]) if block)

    assert "Norway in a Nutshell from Bergen to Oslo" in day_html
    assert "Scenic Rail &amp; Fjord Journey from Bergen to Oslo" not in day_html
