from __future__ import annotations

from app_modules.calculator_component_payload import build_calculator_grid_payload
from app_modules.calculator_library_transport import (
    CalculatorLibraryTransportSignal,
    apply_calculator_library_transport_result,
    apply_calculator_library_transport_signal,
    calculator_library_browser_ack,
    calculator_library_rows_are_acknowledged,
    parse_calculator_library_transport_signal,
)
from app_modules.calculator_state_keys import CALCULATOR_LIBRARY_BROWSER_ACK_KEY
from calculator.calculator_state import CalculatorState
from calculator.library_model import LocalLibraryRow
from calculator.library_store import LocalLibraryReadResult


def test_transport_signal_parser_accepts_only_complete_library_messages() -> None:
    signal = parse_calculator_library_transport_signal(
        {
            "action": "library_transport",
            "library_transport": {
                "status": "retained",
                "fingerprint": "fingerprint",
                "payload_version": "compact-v2",
                "row_count": 2,
            },
        }
    )

    assert signal == CalculatorLibraryTransportSignal("retained", "fingerprint", "compact-v2", 2)
    assert parse_calculator_library_transport_signal({"action": "save"}) is None
    assert parse_calculator_library_transport_signal(
        {"action": "library_transport", "library_transport": {"status": "retained", "row_count": -1}}
    ) is None


def test_exact_ack_is_recorded_and_matching_cache_miss_clears_it() -> None:
    session: dict[str, object] = {}
    signal = CalculatorLibraryTransportSignal("retained", "fp", "compact-v2", 7)

    update = apply_calculator_library_transport_signal(
        session,
        signal,
        expected_fingerprint="fp",
        expected_payload_version="compact-v2",
        expected_row_count=7,
    )

    assert update.changed is True
    assert calculator_library_browser_ack(session) == {
        "fingerprint": "fp",
        "payload_version": "compact-v2",
        "row_count": 7,
    }
    assert calculator_library_rows_are_acknowledged(
        calculator_library_browser_ack(session),
        fingerprint="fp",
        payload_version="compact-v2",
        row_count=7,
    )

    miss = apply_calculator_library_transport_signal(
        session,
        CalculatorLibraryTransportSignal("cache_miss", "fp", "compact-v2", 7),
        expected_fingerprint="fp",
        expected_payload_version="compact-v2",
        expected_row_count=7,
    )
    assert miss.changed is True
    assert CALCULATOR_LIBRARY_BROWSER_ACK_KEY not in session


def test_stale_ack_does_not_replace_current_browser_contract() -> None:
    session: dict[str, object] = {
        CALCULATOR_LIBRARY_BROWSER_ACK_KEY: {
            "fingerprint": "current",
            "payload_version": "compact-v2",
            "row_count": 3,
        }
    }

    update = apply_calculator_library_transport_signal(
        session,
        CalculatorLibraryTransportSignal("retained", "old", "compact-v2", 3),
        expected_fingerprint="current",
        expected_payload_version="compact-v2",
        expected_row_count=3,
    )

    assert update.changed is False
    assert update.status == "ignored_stale_ack"
    assert calculator_library_browser_ack(session)["fingerprint"] == "current"


def test_payload_omits_only_exactly_acknowledged_rows_and_preserves_duplicates() -> None:
    rows = (
        LocalLibraryRow(library_id="Transfers:10", source_sheet="Transfers", source_row=10, travel_element="Same service"),
        LocalLibraryRow(library_id="Transfers:11", source_sheet="Transfers", source_row=11, travel_element="Same service"),
    )
    read = LocalLibraryReadResult(rows, "local_excel", True, fingerprint="workbook-fp")
    first = build_calculator_grid_payload(CalculatorState(), read)

    assert len(first["library_rows"]) == 2
    assert [row["i"] for row in first["library_rows"]] == ["Transfers:10", "Transfers:11"]

    ack = {
        "fingerprint": first["library_fingerprint"],
        "payload_version": first["library_payload_version"],
        "row_count": first["library_row_count"],
    }
    unchanged = build_calculator_grid_payload(CalculatorState(), read, browser_library_ack=ack)
    changed = build_calculator_grid_payload(
        CalculatorState(),
        LocalLibraryReadResult(rows, "local_excel", True, fingerprint="changed-workbook"),
        browser_library_ack=ack,
    )

    assert unchanged["library_rows"] == ()
    assert len(changed["library_rows"]) == 2


def test_transport_result_applies_against_the_exact_rendered_payload() -> None:
    session: dict[str, object] = {}
    payload = {
        "library_fingerprint": "fp",
        "library_payload_version": "compact-v2",
        "library_row_count": 2,
    }
    raw_result = {
        "action": "library_transport",
        "library_transport": {
            "status": "retained",
            "fingerprint": "fp",
            "payload_version": "compact-v2",
            "row_count": 2,
        },
    }

    update = apply_calculator_library_transport_result(session, raw_result, payload)

    assert update is not None
    assert update.changed is True
    assert update.status == "retained"
    assert calculator_library_browser_ack(session)["fingerprint"] == "fp"
    assert apply_calculator_library_transport_result(session, {"action": "sync"}, payload) is None
