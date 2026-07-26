"""Streamlit-side execution of validated Calculator page actions.

The Calculator page owns layout and component orchestration. This module owns
side-effectful action dispatch: navigation, Excel handoff, downloads, generation,
and local-backup open confirmation.
"""

from __future__ import annotations

import base64
import binascii

import streamlit as st

from app_modules.calculator_backup_action import read_calculator_upload_bytes, render_calculator_backup_controls
from app_modules.calculator_component_result import CalculatorGridResult
from app_modules.calculator_download_action import prepare_staged_calculation_download
from app_modules.calculator_navigation import close_calculator_page, open_local_library_page
from app_modules.calculator_open_action import (
    cancel_pending_calculator_import,
    confirm_pending_calculator_import,
    pending_calculator_import,
    request_calculator_upload_import,
)
from app_modules.calculator_state_keys import (
    CALCULATOR_GENERATION_FEEDBACK_KEY,
    CALCULATOR_NOTICE_KEY,
)
from calculator.calculator_state import CalculatorState
from calculator.validation import CalculatorValidationScope, validate_calculator_state


_MAX_CALCULATOR_UPLOAD_BYTES = 12 * 1024 * 1024


def dispatch_calculator_backend_action(
    result: CalculatorGridResult | None,
    state: CalculatorState,
    currency_rates: dict[str, float],
) -> None:
    """Execute one accepted browser action and rerun when state changed."""

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
        open_uploaded_calculator_excel(result)
        return
    if result.action == "generate_agent":
        render_calculator_generation_result(state, output_brand="agent")
        return
    if result.action == "generate_customer":
        render_calculator_generation_result(state, output_brand="booknordics_customer")


def open_uploaded_calculator_excel(result: CalculatorGridResult) -> None:
    """Decode, validate, and stage one browser-selected Calculator workbook."""

    filename = str(result.upload_filename or "calculation.xlsx").strip()
    encoded = str(result.upload_content_base64 or "").strip()
    if not encoded:
        _set_notice("warning", "No Excel file was received.")
        st.rerun()
        return
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        _set_notice("warning", "The selected Excel file could not be read.")
        st.rerun()
        return
    if len(content) > _MAX_CALCULATOR_UPLOAD_BYTES:
        _set_notice("warning", "The selected Excel file is larger than the 12 MB Calculator limit.")
        st.rerun()
        return
    try:
        imported = read_calculator_upload_bytes(content, filename=filename)
    except (ValueError, TypeError) as exc:
        _set_notice("warning", f"Could not open Excel: {exc}")
        st.rerun()
        return

    import_issues = validate_calculator_state(
        imported.state,
        imported.currency_rates,
        scope=CalculatorValidationScope.IMPORT,
    )
    if import_issues:
        _set_notice("warning", import_issues[0].message)
        st.rerun()
        return

    notice = request_calculator_upload_import(
        st.session_state,
        imported,
        filename=filename,
        current_state=result.state,
    )
    if notice is not None:
        _set_notice(notice.level, notice.message)
    st.rerun()


def render_calculator_generation_result(state: CalculatorState, *, output_brand: str) -> None:
    """Run Calculator generation and project its result into page feedback state."""

    from app_modules.calculator_generation_action import generate_itinerary_from_calculator
    from app_modules.validation_gate import block_generation

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
        _set_notice("warning", result.message)
    st.rerun()


def render_calculator_backup_action(state: CalculatorState) -> None:
    """Render the backup upload control and stage or apply a selected backup."""

    imported = render_calculator_backup_controls(state)
    if imported is None:
        return
    notice = request_calculator_upload_import(
        st.session_state,
        imported,
        current_state=state,
    )
    if notice is not None:
        _set_notice(notice.level, notice.message)
    st.rerun()


def render_pending_calculator_import_confirmation() -> bool:
    """Render destructive-open confirmation for a staged local Calculator file."""

    pending = pending_calculator_import(st.session_state)
    if pending is None:
        return False

    label = pending.filename
    if not label:
        label = "calculation Excel" if pending.imported.source == "xlsx" else "Calculator backup"
    st.warning(f"Unsaved changes in the current workspace will be replaced when opening {label}.")
    keep_col, open_col = st.columns(2)
    with keep_col:
        if st.button("Keep current workspace", key="cancel_calculator_import", use_container_width=True):
            cancel_pending_calculator_import(st.session_state)
            _set_notice("info", "Calculator file open cancelled.")
            st.rerun()
            return True
    with open_col:
        if st.button("Open file anyway", key="confirm_calculator_import", use_container_width=True):
            notice = confirm_pending_calculator_import(st.session_state)
            if notice is not None:
                _set_notice(notice.level, notice.message)
            st.rerun()
            return True
    return True


def _set_notice(level: object, message: object) -> None:
    st.session_state[CALCULATOR_NOTICE_KEY] = {
        "level": str(level or "info"),
        "message": str(message or ""),
    }


__all__ = [
    "dispatch_calculator_backend_action",
    "open_uploaded_calculator_excel",
    "render_calculator_backup_action",
    "render_calculator_generation_result",
    "render_pending_calculator_import_confirmation",
]
