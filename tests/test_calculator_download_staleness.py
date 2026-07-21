from __future__ import annotations

from app_modules.calculator_download_action import (
    calculator_download_signature,
    ready_calculation_download_payload,
)
from app_modules.calculator_state_keys import CALCULATOR_READY_DOWNLOAD_KEY
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


def _state(name: str = "Trip") -> CalculatorState:
    return CalculatorState(itinerary_name=name, rows=(CalculatorRow(row_id="1", travel_element="Hotel"),))


def _prepared_payload(*, rate: float = 10.0) -> dict[str, object]:
    return {
        "filename": "Trip.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content_base64": "eGxzeA==",
        "download_signature": calculator_download_signature(_state(), currency_rates={"EUR": rate}),
    }


def test_ready_excel_download_signature_includes_currency_rates() -> None:
    state = _state()

    eur_10 = calculator_download_signature(state, currency_rates={"EUR": 10.0})
    eur_11 = calculator_download_signature(state, currency_rates={"EUR": 11.0})

    assert eur_10 != eur_11


def test_stale_ready_excel_payload_is_removed_before_component_render() -> None:
    session_state: dict[str, object] = {CALCULATOR_READY_DOWNLOAD_KEY: _prepared_payload(rate=10.0)}

    payload = ready_calculation_download_payload(session_state, _state(), currency_rates={"EUR": 11.0})

    assert payload == {}
    assert CALCULATOR_READY_DOWNLOAD_KEY not in session_state


def test_ready_excel_payload_survives_unchanged_state_and_rates() -> None:
    prepared = _prepared_payload(rate=10.0)
    session_state: dict[str, object] = {CALCULATOR_READY_DOWNLOAD_KEY: prepared}

    payload = ready_calculation_download_payload(session_state, _state(), currency_rates={"EUR": 10.0})

    assert payload == prepared
    assert CALCULATOR_READY_DOWNLOAD_KEY in session_state


def test_prepare_download_is_browser_only_and_keeps_one_encoded_workbook_copy(monkeypatch) -> None:
    import app_modules.calculator_download_action as action

    monkeypatch.setattr(
        action,
        "prepare_calculation_download",
        lambda state, currency_rates=None: action.WorkbookExport(
            filename="Trip.xlsx",
            content=b"xlsx",
        ),
    )
    session_state: dict[str, object] = {}

    action.prepare_staged_calculation_download(session_state, _state(), currency_rates={"EUR": 11.0})

    payload = session_state[CALCULATOR_READY_DOWNLOAD_KEY]
    assert payload == {
        "filename": "Trip.xlsx",
        "mime": action.CALCULATION_XLSX_MIME,
        "content_base64": "eGxzeA==",
        "download_signature": calculator_download_signature(_state(), currency_rates={"EUR": 11.0}),
    }
    assert "content" not in payload
    assert "saved_to_cloud" not in payload
    assert "auto_download" not in payload
