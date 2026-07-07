"""Patch BZ1B gates for the dedicated Norway in a Nutshell contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from itinerary_generation.nutshell_domain import (
    NUTSHELL_CONTRACT_KIND,
    NUTSHELL_CONTRACT_VERSION,
    NutshellJourney,
    build_nutshell_journey,
    nutshell_journey_from_row,
)
from itinerary_generation.title_routes import _route_label_from_activity_text
from itinerary_generation.transport_norway import _norway_nutshell_route_label
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


_REAL_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "real_inputs"
    / "scandinavia_cruise_premium_working.txt"
)


def _real_nutshell_row() -> dict:
    rows = normalize_itinerary_rows(parse_itinerary(_REAL_FIXTURE.read_text(encoding="utf-8")))
    return next(
        row
        for row in rows
        if (row.get("activity_product") or {}).get("canonical_family") == "norway_in_a_nutshell"
    )


def test_normalizer_attaches_versioned_contract_with_source_and_commercial_state() -> None:
    row = _real_nutshell_row()
    contract = row["activity_product"]["domain_contract"]
    journey = nutshell_journey_from_row(row)

    assert contract["kind"] == NUTSHELL_CONTRACT_KIND
    assert contract["schema_version"] == NUTSHELL_CONTRACT_VERSION
    assert journey is not None
    assert journey.origin == "Bergen"
    assert journey.destination == "Oslo"
    assert journey.direction == "bergen_to_oslo"
    assert journey.client_title == "Norway in a Nutshell from Bergen to Oslo"
    assert journey.journey_time == "8:00 AM - 8:00 PM"
    assert journey.travel_date == "16.10.2026"
    assert journey.commercial_status == "included"
    assert journey.commercial_reason == "default_included"
    assert journey.source_row_ids == (row["row_id"],)
    assert row["activity_product"]["display_title"] == journey.client_title


def test_timetable_contract_preserves_order_modes_and_times() -> None:
    source = """Norway in a Nutshell from Oslo to Bergen
09:18 Oslo - 14:20 Myrdal via Train
14:41 Myrdal - 15:39 Flåm via Train
17:30 Flåm - 19:20 Gudvangen via Cruise
19:40 Gudvangen - 20:40 Voss via Scenic Bus
21:02 Voss - 22:15 Bergen via Train"""

    journey = build_nutshell_journey(source)

    assert journey is not None
    assert journey.direction == "oslo_to_bergen"
    assert journey.route_points == ("Oslo", "Myrdal", "Flåm", "Gudvangen", "Voss", "Bergen")
    assert [leg.mode for leg in journey.legs] == ["Train", "Train", "Cruise", "Scenic Bus", "Train"]
    assert journey.legs[0].departure_time == "9:18 AM"
    assert journey.legs[-1].arrival_time == "10:15 PM"
    assert journey.warnings == ()


def test_partial_source_keeps_known_legs_without_inventing_times() -> None:
    source = (
        "Norway in a Nutshell from Oslo to Bergen - Includes: "
        "Train Oslo to Myrdal, Flåm Railway Myrdal to Flåm, "
        "Fjord Cruise Flåm to Gudvangen, Coach Gudvangen to Voss, "
        "Train Voss to Bergen"
    )

    journey = build_nutshell_journey(source)

    assert journey is not None
    assert journey.route_points == ("Oslo", "Myrdal", "Flåm", "Gudvangen", "Voss", "Bergen")
    assert [leg.mode for leg in journey.legs] == ["Train", "Flåm Railway", "Fjord Cruise", "Coach", "Train"]
    assert all(not leg.departure_time and not leg.arrival_time for leg in journey.legs)
    assert journey.warnings == ()


def test_conflicting_supplier_chain_is_reported_not_silently_repaired() -> None:
    journey = nutshell_journey_from_row(_real_nutshell_row())

    assert journey is not None
    assert journey.route_points == ("Bergen", "Oslo")
    assert "route_leg_discontinuity" in journey.warnings
    assert [leg.source_text for leg in journey.legs[:2]] == [
        "E-tickets for Voss railway: Bergen to Oslo",
        "E-tickets for bus: Voss to Gudvangen",
    ]


def test_legacy_title_entry_points_use_the_same_contract_title() -> None:
    source = (
        "Norway in a Nutshell from Oslo to Bergen "
        "Norway in a Nutshell | Oslo to Bergen | 08:35 - 20:38"
    )
    journey = build_nutshell_journey(source)

    assert journey is not None
    assert journey.client_title == "Norway in a Nutshell from Oslo to Bergen"
    assert _route_label_from_activity_text(source) == journey.client_title
    assert _norway_nutshell_route_label(source) == journey.client_title


def test_contract_metadata_round_trip_is_lossless() -> None:
    journey = build_nutshell_journey(
        "Norway in a Nutshell from Oslo to Bergen - Includes: "
        "Train Oslo to Myrdal, Flåm Railway Myrdal to Flåm"
    )

    assert journey is not None
    restored = NutshellJourney.from_metadata(journey.as_metadata)
    assert restored == journey


def test_contract_rejects_wrong_kind_or_version() -> None:
    with pytest.raises(ValueError, match="Not a Norway in a Nutshell"):
        NutshellJourney.from_metadata({"kind": "generic_transport", "schema_version": 1})

    with pytest.raises(ValueError, match="Unsupported Norway in a Nutshell"):
        NutshellJourney.from_metadata(
            {"kind": NUTSHELL_CONTRACT_KIND, "schema_version": NUTSHELL_CONTRACT_VERSION + 1}
        )


def test_non_nutshell_rows_do_not_receive_a_domain_contract() -> None:
    row = normalize_itinerary_rows(
        parse_itinerary("Day 1\tTrain\t01/09/2026\t\tOslo\tTrain from Oslo to Lillehammer")
    )[0]

    assert (row.get("activity_product") or {}).get("domain_contract") is None
    assert nutshell_journey_from_row(row) is None


def test_explicit_non_nutshell_product_identity_wins_over_route_markers() -> None:
    raw = (
        'Day 1\tActivity\t01/06/2026\t\tBergen\t'
        'Bergen: Guided Day Tour to Flåm incl. Flåm Railway & Fjord Cruise - '
        'Includes: Coach Bergen to Gudvangen, Fjord Cruise Gudvangen to Flåm, '
        'Flåm Railway Flåm to Myrdal, Coach Voss to Bergen'
    )
    row = normalize_itinerary_rows(parse_itinerary(raw))[0]

    assert row["activity_product"]["canonical_family"] == "bergen_guided_flam_day_tour"
    assert row["title"] == "Bergen Guided Day Tour to Flåm with Flåm Railway & Fjord Cruise"
    assert row["activity_product"].get("domain_contract") is None
