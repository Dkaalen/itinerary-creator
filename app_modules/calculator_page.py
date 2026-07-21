"""Render the in-app itinerary calculator page."""

from __future__ import annotations

import base64
import binascii

import streamlit as st

from app_modules.app_header import _render_app_header
from app_modules.calculator_backup_action import (
    read_calculator_upload_bytes,
    render_calculator_backup_controls,
)
from app_modules.calculator_component_payload import build_calculator_grid_payload
from app_modules.calculator_component_protocol import (
    acknowledge_calculator_grid_result,
    authorize_calculator_grid_result,
    calculator_component_ack_payload,
)
from app_modules.calculator_component_result import CalculatorGridResult, parse_calculator_grid_result
from app_modules.calculator_currency_controls import render_currency_rate_editor
from app_modules.calculator_download_action import (
    prepare_staged_calculation_download,
    ready_calculation_download_payload,
)
from app_modules.calculator_generation_action import generate_itinerary_from_calculator
from app_modules.calculator_library_cache import read_cached_local_library
from app_modules.calculator_library_controls import (
    render_local_library_refresh_control,
    render_local_library_status,
)
from app_modules.calculator_navigation import calculator_draft_namespace, close_calculator_page, open_local_library_page
from app_modules.calculator_open_action import apply_calculator_upload_import
from app_modules.calculator_session_state import (
    apply_calculator_grid_result,
    calculator_state_from_session,
    sync_calculator_itinerary_name_input,
    update_calculator_itinerary_name,
)
from app_modules.calculator_state_keys import (
    CALCULATOR_NOTICE_KEY,
    CALCULATOR_ADVANCED_TOGGLE_KEY,
    CALCULATOR_ITINERARY_NAME_INPUT_KEY,
    CALCULATOR_GENERATION_FEEDBACK_KEY,
    CURRENCY_RATES_STATE_KEY,
)
from app_modules.input_workspace import render_studio_brand
from app_modules.validation_gate import block_generation, render_blocking_issues
from ui.style_calculator import CALCULATOR_PAGE_CSS
from calculator.calculator_state import CalculatorState
from calculator_grid_component import render_calculator_grid

_COMPONENT_KEY = "calculator_browser_grid"
# Navigation labels are rendered by the synchronized browser grid: Back to workspace; Manage Local Library.


def render_calculator_page(app_version: str) -> None:
    """Render the standalone calculator page."""

    _render_calculator_page_css()
    state = calculator_state_from_session(st.session_state)
    _render_app_header(app_version, stage="input")
    _render_calculator_topbar()
    _render_calculator_header()
    _render_calculator_notice()
    _render_generation_feedback()
    refresh_library = render_local_library_refresh_control()
    library_read = read_cached_local_library(st.session_state, force_refresh=refresh_library)
    if CURRENCY_RATES_STATE_KEY not in st.session_state and library_read.currency_rates:
        st.session_state[CURRENCY_RATES_STATE_KEY] = dict(library_read.currency_rates)
    currency_rates = render_currency_rate_editor(st.session_state)
    render_local_library_status(library_read, refreshed=refresh_library)

    sync_calculator_itinerary_name_input(st.session_state)
    itinerary_name = st.text_input(
        "Itinerary name",
        key=CALCULATOR_ITINERARY_NAME_INPUT_KEY,
    )
    state = update_calculator_itinerary_name(st.session_state, itinerary_name)

    pending_download = ready_calculation_download_payload(
        st.session_state,
        state,
        currency_rates=currency_rates,
    )
    payload = build_calculator_grid_payload(
        state,
        library_read,
        show_advanced=bool(st.session_state.get(CALCULATOR_ADVANCED_TOGGLE_KEY, False)),
        currency_rates=currency_rates,
        draft_namespace=_calculator_draft_namespace(),
        pending_download=pending_download,
        component_ack=calculator_component_ack_payload(st.session_state),
    )
    raw_result = render_calculator_grid(payload, key=_COMPONENT_KEY)
    parsed_result = parse_calculator_grid_result(raw_result, itinerary_name)
    accepted_result = _accept_component_result(parsed_result, state)
    if accepted_result is not None:
        state = _apply_component_result(accepted_result)
        acknowledge_calculator_grid_result(
            st.session_state,
            accepted_result,
            status="accepted",
            server_state=state,
        )

    _render_backend_action(accepted_result, state, currency_rates)
    _render_backup_controls(state)



def _accept_component_result(
    result: CalculatorGridResult | None,
    current_state: CalculatorState,
) -> CalculatorGridResult | None:
    if result is None:
        return None
    decision = authorize_calculator_grid_result(st.session_state, result, current_state)
    if decision.should_process:
        return result
    if decision.duplicate:
        return None
    st.session_state[CALCULATOR_NOTICE_KEY] = {"level": "warning", "message": decision.message}
    st.rerun()
    return None


def _calculator_draft_namespace() -> str:
    return calculator_draft_namespace(st.session_state)


def _apply_component_result(result: CalculatorGridResult) -> CalculatorState:
    return apply_calculator_grid_result(st.session_state, result)


def _render_calculator_topbar() -> None:
    """Render branding only; navigation lives inside the synchronized grid."""

    render_studio_brand()


def _render_calculator_header() -> None:
    st.html(
        """
        <section class="workspace-page-heading calculator-heading">
          <span class="calculator-kicker">Calculator workspace</span>
          <h1>Calculator</h1>
        </section>
        """
    )


def _render_backend_action(
    result: CalculatorGridResult | None,
    state: CalculatorState,
    currency_rates: dict[str, float],
) -> None:
    if result is None:
        return
    if result.action == "close":
        close_calculator_page(st.session_state)
        st.rerun()
        return
    if result.action == "open_library":
        open_local_library_page(st.session_state)
        st.rerun()
        return
    if result.action == "download":
        prepare_staged_calculation_download(st.session_state, state, currency_rates=currency_rates)
        st.rerun()
        return
    if result.action == "sync":
        st.rerun()
        return
    if result.action == "open_excel":
        _open_uploaded_excel(result)
        return
    if result.action == "generate_agent":
        _render_generation_result(state, output_brand="agent")
        return
    if result.action == "generate_customer":
        _render_generation_result(state, output_brand="booknordics_customer")


def _render_calculator_notice() -> None:
    notice = st.session_state.pop(CALCULATOR_NOTICE_KEY, None)
    if not isinstance(notice, dict):
        return
    message = str(notice.get("message") or "").strip()
    if not message:
        return
    level = str(notice.get("level") or "info")
    renderer = getattr(st, level, st.info)
    renderer(message)


def _render_generation_feedback() -> None:
    report = st.session_state.pop(CALCULATOR_GENERATION_FEEDBACK_KEY, None)
    if report is not None:
        render_blocking_issues(report)


def _open_uploaded_excel(result: CalculatorGridResult) -> None:
    filename = str(result.upload_filename or "calculation.xlsx").strip()
    encoded = str(result.upload_content_base64 or "").strip()
    if not encoded:
        st.session_state[CALCULATOR_NOTICE_KEY] = {"level": "warning", "message": "No Excel file was received."}
        st.rerun()
        return
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        st.session_state[CALCULATOR_NOTICE_KEY] = {"level": "warning", "message": "The selected Excel file could not be read."}
        st.rerun()
        return
    if len(content) > 12 * 1024 * 1024:
        st.session_state[CALCULATOR_NOTICE_KEY] = {"level": "warning", "message": "The selected Excel file is larger than the 12 MB Calculator limit."}
        st.rerun()
        return
    try:
        imported = read_calculator_upload_bytes(content, filename=filename)
    except (ValueError, TypeError) as exc:
        st.session_state[CALCULATOR_NOTICE_KEY] = {"level": "warning", "message": f"Could not open Excel: {exc}"}
        st.rerun()
        return

    notice = apply_calculator_upload_import(st.session_state, imported, filename=filename)
    st.session_state[CALCULATOR_NOTICE_KEY] = {"level": notice.level, "message": notice.message}
    st.rerun()


def _render_generation_result(state: CalculatorState, *, output_brand: str) -> None:
    with st.spinner("Building your itinerary…"):
        result = generate_itinerary_from_calculator(st.session_state, state, output_brand=output_brand)

    if result.ok:
        st.rerun()
        return

    validation_report = (result.payload or {}).get("validation_report") if result.payload else None
    if validation_report is not None:
        block_generation(validation_report)
        st.session_state[CALCULATOR_GENERATION_FEEDBACK_KEY] = validation_report
    elif result.message:
        st.session_state[CALCULATOR_NOTICE_KEY] = {"level": "warning", "message": result.message}
    st.rerun()


def _render_backup_controls(state: CalculatorState) -> None:
    imported = render_calculator_backup_controls(state)
    if imported is None:
        return
    notice = apply_calculator_upload_import(st.session_state, imported)
    st.session_state[CALCULATOR_NOTICE_KEY] = {"level": notice.level, "message": notice.message}
    st.rerun()


def _render_calculator_page_css() -> None:
    """Apply calculator-specific CSS from the UI style layer."""

    st.markdown(f"<style>{CALCULATOR_PAGE_CSS}</style>", unsafe_allow_html=True)
