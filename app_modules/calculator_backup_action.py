"""Render calculator backup and Excel reopen controls."""

from __future__ import annotations

from dataclasses import dataclass


from calculator.calculator_state import CalculatorState
from calculator.filename_sanitizer import sanitize_filename_stem
from calculator.state_serialization import calculator_state_from_json, calculator_state_to_json
from calculator.workbook_import import import_calculation_workbook

CALCULATOR_BACKUP_MIME = "application/json"


@dataclass(frozen=True)
class CalculatorBackupDownload:
    """Prepared calculator backup download payload."""

    filename: str
    content: bytes


@dataclass(frozen=True)
class CalculatorUploadImport:
    """One reopened calculator plus optional workbook currency rates."""

    state: CalculatorState
    currency_rates: dict[str, float] | None = None
    warnings: tuple[str, ...] = ()
    source: str = "json"


def prepare_calculator_backup_download(state: CalculatorState) -> CalculatorBackupDownload:
    """Return a JSON backup payload for the current calculator state."""

    stem = sanitize_filename_stem(state.itinerary_name or "Calculation")
    content = calculator_state_to_json(state).encode("utf-8")
    return CalculatorBackupDownload(filename=f"{stem} - Calculator Backup.json", content=content)


def read_calculator_backup(uploaded_file: object) -> CalculatorState:
    """Read calculator state from a Streamlit uploaded JSON file object."""

    return calculator_state_from_json(_uploaded_bytes(uploaded_file))


def read_calculator_upload(uploaded_file: object) -> CalculatorUploadImport:
    """Read either a JSON backup or a compatible calculator Excel workbook."""

    content = _uploaded_bytes(uploaded_file)
    filename = str(getattr(uploaded_file, "name", "") or "")
    if filename.lower().endswith(".xlsx") or content.startswith(b"PK"):
        imported = import_calculation_workbook(content, filename=filename)
        return CalculatorUploadImport(
            state=imported.state,
            currency_rates=imported.currency_rates,
            warnings=imported.warnings,
            source="xlsx",
        )
    return CalculatorUploadImport(state=calculator_state_from_json(content), source="json")


def render_calculator_backup_controls(state: CalculatorState) -> CalculatorUploadImport | None:
    """Render backup controls and return imported state/rates when provided."""

    import streamlit as st

    with st.expander("Advanced: backup / reopen calculator", expanded=False):
        backup = prepare_calculator_backup_download(state)
        st.download_button(
            label="Download backup to reopen later",
            data=backup.content,
            file_name=backup.filename,
            mime=CALCULATOR_BACKUP_MIME,
            use_container_width=True,
        )
        uploaded_file = st.file_uploader(
            "Choose calculator backup JSON or calculation Excel",
            type=("json", "xlsx"),
            accept_multiple_files=False,
            key="calculator_backup_upload",
        )
        if uploaded_file is None:
            return None
        if not st.button("Reopen selected calculation", use_container_width=True):
            return None
        try:
            imported = read_calculator_upload(uploaded_file)
        except (ValueError, TypeError) as exc:
            st.warning(f"Could not open calculator file: {exc}")
            return None
        for warning in imported.warnings:
            st.warning(warning)
        return imported


def _uploaded_bytes(uploaded_file: object) -> bytes:
    if hasattr(uploaded_file, "getvalue"):
        return bytes(uploaded_file.getvalue())
    if hasattr(uploaded_file, "read"):
        return bytes(uploaded_file.read())
    raise ValueError("Unsupported calculator upload.")
