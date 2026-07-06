"""Render the in-app itinerary calculator page."""

from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header
from app_modules.calculator_backup_action import render_calculator_backup_controls
from app_modules.calculator_component_payload import build_calculator_grid_payload
from app_modules.calculator_component_result import CalculatorGridResult, parse_calculator_grid_result
from app_modules.calculator_currency_controls import render_currency_rate_editor
from app_modules.calculator_download_action import render_calculation_download_button
from app_modules.calculator_generation_action import generate_itinerary_from_calculator
from app_modules.calculator_library_cache import read_cached_local_library
from app_modules.calculator_library_controls import (
    render_local_library_refresh_control,
    render_local_library_status,
)
from app_modules.calculator_navigation import CALCULATOR_STATE_KEY, calculator_draft_namespace, close_calculator_page, open_local_library_page
from app_modules.validation_gate import block_generation, render_blocking_issues
from calculator.calculator_state import CalculatorState, create_initial_calculator_state
from calculator_grid_component import render_calculator_grid

_ADVANCED_TOGGLE_STATE_KEY = "calculator_component_show_advanced"
_COMPONENT_KEY = "calculator_browser_grid"


def render_calculator_page(app_version: str) -> None:
    """Render the standalone calculator page."""

    _render_calculator_page_width_css()
    state = _calculator_state_from_session()
    _render_app_header(app_version, stage="input")
    _render_calculator_topbar()
    _render_calculator_header()
    currency_rates = render_currency_rate_editor(st.session_state)
    refresh_library = render_local_library_refresh_control()
    library_read = read_cached_local_library(st.session_state, force_refresh=refresh_library)
    render_local_library_status(library_read, refreshed=refresh_library)

    itinerary_name = st.text_input(
        "Itinerary name",
        value=state.itinerary_name,
        key="calculator_itinerary_name_input",
    )
    state = state.with_itinerary_name(itinerary_name)
    _store_calculator_state(state)

    payload = build_calculator_grid_payload(
        state,
        library_read,
        show_advanced=bool(st.session_state.get(_ADVANCED_TOGGLE_STATE_KEY, False)),
        currency_rates=currency_rates,
        draft_namespace=_calculator_draft_namespace(),
    )
    raw_result = render_calculator_grid(payload, key=_COMPONENT_KEY)
    parsed_result = parse_calculator_grid_result(raw_result, itinerary_name)
    if parsed_result is not None:
        state = _apply_component_result(parsed_result)

    _render_backend_action(parsed_result, state, currency_rates)
    _render_backup_controls(state)


def _calculator_state_from_session() -> CalculatorState:
    state = st.session_state.get(CALCULATOR_STATE_KEY)
    if isinstance(state, CalculatorState) and state.rows:
        return state
    new_state = create_initial_calculator_state(str(getattr(state, "itinerary_name", "") or st.session_state.get("itinerary_name") or ""))
    _store_calculator_state(new_state)
    return new_state


def _store_calculator_state(state: CalculatorState) -> None:
    st.session_state[CALCULATOR_STATE_KEY] = state


def _calculator_draft_namespace() -> str:
    return calculator_draft_namespace(st.session_state)


def _apply_component_result(result: CalculatorGridResult) -> CalculatorState:
    st.session_state[_ADVANCED_TOGGLE_STATE_KEY] = result.show_advanced
    _store_calculator_state(result.state)
    return result.state


def _render_calculator_topbar() -> None:
    brand_col, back_col, library_col = st.columns([0.58, 0.20, 0.22], vertical_alignment="center")
    with brand_col:
        st.html('<div class="studio-toolbar"><span class="studio-wordmark">Itinerary Studio</span></div>')
    with back_col:
        if st.button("Back to workspace", use_container_width=True):
            close_calculator_page(st.session_state)
            st.rerun()
    with library_col:
        if st.button("Manage Local Library", use_container_width=True):
            open_local_library_page(st.session_state)
            st.rerun()


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
    if result.action == "download":
        st.success("Excel export is ready.")
        render_calculation_download_button(state, currency_rates=currency_rates)
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
    imported_state = render_calculator_backup_controls(state)
    if imported_state is None:
        return
    _store_calculator_state(imported_state)
    st.success("Calculator backup reopened.")
    st.rerun()


def _render_calculator_page_width_css() -> None:
    """Give the spreadsheet room without turning the page into an edge-to-edge strip."""

    st.markdown(
        """
        <style>
        section.main > div.block-container,
        .main .block-container,
        [data-testid="stAppViewContainer"] .block-container {
            max-width: min(100% - 3rem, 1540px) !important;
            width: min(100% - 3rem, 1540px) !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        div[data-testid="stCustomComponentV1"],
        div[data-testid="element-container"]:has(iframe[title="calculator_grid"]),
        div:has(> iframe[title="calculator_grid"]) {
            width: 100% !important;
            max-width: 100% !important;
            margin-left: 0 !important;
            margin-right: 0 !important;
        }
        iframe[title="calculator_grid"],
        div[data-testid="stCustomComponentV1"] iframe {
            width: 100% !important;
            max-width: 100% !important;
            border-radius: 18px !important;
            border: 1px solid rgba(199, 188, 170, 0.62) !important;
            box-shadow: none !important;
            background: var(--paper) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
