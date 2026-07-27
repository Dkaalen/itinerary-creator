"""Render the in-app itinerary calculator page."""

from __future__ import annotations

import streamlit as st

from app_modules.app_header import _render_app_header
from app_modules.calculator_action_policy import (
    calculator_action_updates_session_state,
    calculator_action_validation_issues,
)
from app_modules.calculator_page_actions import (
    dispatch_calculator_backend_action,
    render_calculator_backup_action,
    render_pending_calculator_import_confirmation,
)
from app_modules.calculator_component_payload import build_calculator_grid_payload
from app_modules.calculator_component_protocol import (
    acknowledge_calculator_grid_result,
    authorize_calculator_grid_result,
    calculator_component_ack_payload,
)
from app_modules.calculator_component_result import CalculatorGridResult, parse_calculator_grid_result
from app_modules.calculator_currency_controls import render_currency_rate_editor
from app_modules.calculator_download_action import ready_calculation_download_payload
from app_modules.calculator_library_cache import read_cached_local_library
from app_modules.calculator_library_transport import (
    apply_calculator_library_transport_result,
    calculator_library_browser_ack,
)
from app_modules.calculator_library_controls import (
    render_local_library_refresh_control,
    render_local_library_status,
)
from app_modules.calculator_navigation import calculator_draft_namespace, render_back_to_main_page_button
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
from ui.style_calculator import CALCULATOR_PAGE_CSS
from calculator.calculator_state import CalculatorState
from calculator_grid_component import render_calculator_grid

_COMPONENT_KEY = "calculator_browser_grid"
# The browser grid also exposes synchronized navigation; the page-level back action remains independently available.


def render_calculator_page(app_version: str) -> None:
    """Render the standalone calculator page."""

    _render_calculator_page_css()
    state = calculator_state_from_session(st.session_state)
    _render_app_header(app_version, stage="input")
    _render_calculator_topbar()
    _render_calculator_header()
    _render_calculator_notice()
    if render_pending_calculator_import_confirmation():
        return
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
    draft_namespace = _calculator_draft_namespace()
    payload = build_calculator_grid_payload(
        state,
        library_read,
        show_advanced=bool(st.session_state.get(CALCULATOR_ADVANCED_TOGGLE_KEY, False)),
        currency_rates=currency_rates,
        draft_namespace=draft_namespace,
        project_identity=draft_namespace,
        pending_download=pending_download,
        component_ack=calculator_component_ack_payload(st.session_state),
        browser_library_ack=calculator_library_browser_ack(st.session_state),
    )
    raw_result = render_calculator_grid(payload, key=_COMPONENT_KEY)
    library_transport_update = apply_calculator_library_transport_result(st.session_state, raw_result, payload)
    if library_transport_update is not None:
        if library_transport_update.changed:
            st.rerun()
            return
        raw_result = None
    parsed_result = parse_calculator_grid_result(raw_result, itinerary_name)
    accepted_result = _accept_component_result(parsed_result, state)
    if accepted_result is not None:
        action_issues = calculator_action_validation_issues(accepted_result, currency_rates)
        if action_issues:
            acknowledge_calculator_grid_result(
                st.session_state,
                accepted_result,
                status="rejected_validation",
                message=action_issues[0].message,
                server_state=state,
            )
            st.session_state[CALCULATOR_NOTICE_KEY] = {
                "level": "warning",
                "message": action_issues[0].message,
            }
            st.rerun()
            return

        result_state = accepted_result.state
        state_was_applied = calculator_action_updates_session_state(accepted_result, currency_rates)
        if state_was_applied:
            state = _apply_component_result(accepted_result)
        acknowledge_calculator_grid_result(
            st.session_state,
            accepted_result,
            status="accepted" if state_was_applied else "accepted_transient",
            message=(
                "Draft kept in the browser until its highlighted values are resolved."
                if not state_was_applied
                else ""
            ),
            server_state=state,
        )
    else:
        result_state = state

    dispatch_calculator_backend_action(accepted_result, result_state, currency_rates)
    render_calculator_backup_action(state)



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
    """Render page-level branding and a reliable route back to the workspace."""

    with st.container(key="calculator_topbar"):
        brand_col, back_col = st.columns([0.76, 0.24], gap="small", vertical_alignment="center")
        with brand_col:
            render_studio_brand()
        with back_col:
            render_back_to_main_page_button(use_container_width=True)


def _render_calculator_header() -> None:
    st.html(
        """
        <section class="workspace-page-heading calculator-heading">
          <span class="calculator-kicker">Calculator workspace</span>
          <h1>Calculator</h1>
        </section>
        """
    )


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
        from app_modules.validation_gate import render_blocking_issues

        render_blocking_issues(report)


def _render_calculator_page_css() -> None:
    """Apply calculator-specific CSS from the UI style layer."""

    st.markdown(f"<style>{CALCULATOR_PAGE_CSS}</style>", unsafe_allow_html=True)
