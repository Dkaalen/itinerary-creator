"""Render the in-app itinerary calculator page."""

from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header
from app_modules.input_workspace import render_studio_brand
from app_modules.calculator_backup_action import render_calculator_backup_controls
from app_modules.calculator_component_payload import build_calculator_grid_payload
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
from app_modules.calculator_session_state import (
    apply_calculator_grid_result,
    calculator_state_from_session,
    store_calculator_state,
    sync_calculator_itinerary_name_input,
    update_calculator_itinerary_name,
)
from app_modules.calculator_state_keys import (
    CALCULATOR_ADVANCED_TOGGLE_KEY,
    CALCULATOR_ITINERARY_NAME_INPUT_KEY,
    CURRENCY_RATES_STATE_KEY,
)
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
    currency_rates = render_currency_rate_editor(st.session_state)
    refresh_library = render_local_library_refresh_control()
    library_read = read_cached_local_library(st.session_state, force_refresh=refresh_library)
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
    )
    raw_result = render_calculator_grid(payload, key=_COMPONENT_KEY)
    parsed_result = parse_calculator_grid_result(raw_result, itinerary_name)
    if parsed_result is not None:
        state = _apply_component_result(parsed_result)

    _render_backend_action(parsed_result, state, currency_rates)
    _render_backup_controls(state)


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
    if result.action == "generate_agent":
        _render_generation_result(state, output_brand="agent")
        return
    if result.action == "generate_customer":
        _render_generation_result(state, output_brand="booknordics_customer")


def _render_generation_result(state: CalculatorState, *, output_brand: str) -> None:
    with st.spinner("Building your itinerary…"):
        result = generate_itinerary_from_calculator(st.session_state, state, output_brand=output_brand)

    if result.ok:
        st.rerun()
        return

    validation_report = (result.payload or {}).get("validation_report") if result.payload else None
    if validation_report is not None:
        block_generation(validation_report)
        render_blocking_issues(validation_report)
    elif result.message:
        st.warning(result.message)


def _render_backup_controls(state: CalculatorState) -> None:
    imported = render_calculator_backup_controls(state)
    if imported is None:
        return
    if imported.currency_rates:
        st.session_state[CURRENCY_RATES_STATE_KEY] = imported.currency_rates
        for code, value in imported.currency_rates.items():
            st.session_state[f"calculator_currency_rate_{code}"] = float(value)
    store_calculator_state(st.session_state, imported.state, sync_name_input=True)
    message = "Calculation Excel reopened." if imported.source == "xlsx" else "Calculator backup reopened."
    st.success(message)
    st.rerun()



def _render_calculator_page_css() -> None:
    """Apply calculator-specific CSS from the UI style layer."""

    st.markdown(f"<style>{CALCULATOR_PAGE_CSS}</style>", unsafe_allow_html=True)
