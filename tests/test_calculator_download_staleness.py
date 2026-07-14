from __future__ import annotations

from app_modules.calculator_download_action import (
    calculator_download_signature,
    ready_calculation_download_payload,
    render_ready_calculation_download,
)
from app_modules.calculator_state_keys import CALCULATOR_READY_DOWNLOAD_KEY
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from tests.support.streamlit_stub import install_streamlit_stub


def _state(name: str = "Trip") -> CalculatorState:
    return CalculatorState(itinerary_name=name, rows=(CalculatorRow(row_id="1", travel_element="Hotel"),))


def test_ready_excel_download_signature_includes_currency_rates() -> None:
    state = _state()

    eur_10 = calculator_download_signature(state, currency_rates={"EUR": 10.0})
    eur_11 = calculator_download_signature(state, currency_rates={"EUR": 11.0})

    assert eur_10 != eur_11


def test_ready_excel_download_is_cleared_when_calculator_or_rates_change(monkeypatch) -> None:
    import app_modules.calculator_download_action as action

    st = install_streamlit_stub(force=True)
    messages: list[str] = []
    monkeypatch.setattr(action, "st", st)
    monkeypatch.setattr(st, "info", lambda message, *args, **kwargs: messages.append(str(message)))
    session_state: dict[str, object] = {
        CALCULATOR_READY_DOWNLOAD_KEY: {
            "filename": "Trip.xlsx",
            "mime": action.CALCULATION_XLSX_MIME,
            "content": b"xlsx",
            "saved_to_cloud": False,
            "download_signature": calculator_download_signature(_state(), currency_rates={"EUR": 10.0}),
        }
    }

    render_ready_calculation_download(session_state, _state(), currency_rates={"EUR": 11.0})

    assert CALCULATOR_READY_DOWNLOAD_KEY not in session_state
    assert messages == ["Prepared Excel was cleared because the calculator changed. Prepare the download again."]


def test_ready_excel_download_survives_unchanged_state_and_rates(monkeypatch) -> None:
    import app_modules.calculator_download_action as action

    st = install_streamlit_stub(force=True)
    downloads: list[dict] = []
    monkeypatch.setattr(action, "st", st)
    monkeypatch.setattr(st, "download_button", lambda *args, **kwargs: downloads.append(kwargs))
    session_state: dict[str, object] = {
        CALCULATOR_READY_DOWNLOAD_KEY: {
            "filename": "Trip.xlsx",
            "mime": action.CALCULATION_XLSX_MIME,
            "content": b"xlsx",
            "saved_to_cloud": False,
            "download_signature": calculator_download_signature(_state(), currency_rates={"EUR": 10.0}),
        }
    }

    render_ready_calculation_download(session_state, _state(), currency_rates={"EUR": 10.0})

    assert CALCULATOR_READY_DOWNLOAD_KEY in session_state
    assert downloads and downloads[0]["file_name"] == "Trip.xlsx"


def test_ready_excel_payload_is_embedded_for_the_grid_download() -> None:
    session_state: dict[str, object] = {
        CALCULATOR_READY_DOWNLOAD_KEY: {
            "filename": "Trip.xlsx",
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "content": b"xlsx",
            "saved_to_cloud": True,
            "download_signature": calculator_download_signature(_state(), currency_rates={"EUR": 10.0}),
        }
    }

    payload = ready_calculation_download_payload(session_state, _state(), currency_rates={"EUR": 10.0})

    assert payload == {
        "filename": "Trip.xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content_base64": "eGxzeA==",
        "saved_to_cloud": True,
    }


def test_stale_ready_excel_payload_is_removed_before_component_render() -> None:
    session_state: dict[str, object] = {
        CALCULATOR_READY_DOWNLOAD_KEY: {
            "filename": "Trip.xlsx",
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "content": b"xlsx",
            "saved_to_cloud": False,
            "download_signature": calculator_download_signature(_state(), currency_rates={"EUR": 10.0}),
        }
    }

    payload = ready_calculation_download_payload(session_state, _state(), currency_rates={"EUR": 11.0})

    assert payload == {}
    assert CALCULATOR_READY_DOWNLOAD_KEY not in session_state
