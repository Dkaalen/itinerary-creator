"""Apply local Calculator file imports at a safe project boundary."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

from app_modules.calculator_backup_action import CalculatorUploadImport
from app_modules.calculator_restore import restore_calculator_workspace
from app_modules.calculator_state_keys import CALCULATOR_PENDING_IMPORT_KEY
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.calculator_lifecycle import begin_local_calculator_import
from calculator.calculator_state import CalculatorState


@dataclass(frozen=True)
class CalculatorOpenNotice:
    """User-facing result of opening one local Calculator file."""

    level: str
    message: str


@dataclass(frozen=True)
class PendingCalculatorImport:
    """One validated local Calculator import awaiting destructive confirmation."""

    imported: CalculatorUploadImport
    filename: str = ""


def apply_calculator_upload_import(
    session_state: MutableMapping[str, Any],
    imported: CalculatorUploadImport,
    *,
    filename: str = "",
) -> CalculatorOpenNotice:
    """Replace Calculator state without retaining an unrelated cloud identity.

    A local workbook is a new in-memory project. Detaching it from the active
    cloud project prevents a later Save action from silently overwriting the
    project that happened to be open before the import.
    """

    begin_local_calculator_import(session_state)

    if imported.currency_rates is None:
        restore_calculator_workspace(
            session_state,
            imported.state,
            sync_name_input=True,
        )
    else:
        rates = {str(code).upper(): float(value) for code, value in imported.currency_rates.items()}
        restore_calculator_workspace(
            session_state,
            imported.state,
            currency_rates=rates,
            sync_name_input=True,
        )
    return _open_notice(imported, filename=filename)


def request_calculator_upload_import(
    session_state: MutableMapping[str, Any],
    imported: CalculatorUploadImport,
    *,
    filename: str = "",
    current_state: CalculatorState | None = None,
) -> CalculatorOpenNotice | None:
    """Apply a clean import immediately or stage it behind one confirmation.

    The browser-grid Excel action carries the latest rows even when they have
    not yet become the backend authority. Passing ``current_state`` therefore
    prevents a file reopen from bypassing unsaved-work detection.
    """

    if active_project_has_unsaved_changes(session_state, calculator_state=current_state):
        session_state[CALCULATOR_PENDING_IMPORT_KEY] = PendingCalculatorImport(
            imported=imported,
            filename=str(filename or "").strip(),
        )
        return None
    return apply_calculator_upload_import(session_state, imported, filename=filename)


def pending_calculator_import(state: MutableMapping[str, Any]) -> PendingCalculatorImport | None:
    pending = state.get(CALCULATOR_PENDING_IMPORT_KEY)
    return pending if isinstance(pending, PendingCalculatorImport) else None


def cancel_pending_calculator_import(state: MutableMapping[str, Any]) -> None:
    state.pop(CALCULATOR_PENDING_IMPORT_KEY, None)


def confirm_pending_calculator_import(state: MutableMapping[str, Any]) -> CalculatorOpenNotice | None:
    pending = pending_calculator_import(state)
    state.pop(CALCULATOR_PENDING_IMPORT_KEY, None)
    if pending is None:
        return None
    return apply_calculator_upload_import(
        state,
        pending.imported,
        filename=pending.filename,
    )


def _open_notice(imported: CalculatorUploadImport, *, filename: str) -> CalculatorOpenNotice:
    label = str(filename or "").strip()
    if not label:
        label = "calculation Excel" if imported.source == "xlsx" else "Calculator backup"

    warnings = tuple(str(item).strip() for item in imported.warnings if str(item).strip())
    if not warnings:
        return CalculatorOpenNotice(level="success", message=f"Opened {label}.")

    preview = "; ".join(warnings[:3])
    if len(warnings) > 3:
        preview += f"; plus {len(warnings) - 3} more"
    return CalculatorOpenNotice(
        level="warning",
        message=f"Opened {label}. Review import warnings: {preview}.",
    )


__all__ = [
    "CalculatorOpenNotice",
    "PendingCalculatorImport",
    "apply_calculator_upload_import",
    "cancel_pending_calculator_import",
    "confirm_pending_calculator_import",
    "pending_calculator_import",
    "request_calculator_upload_import",
]
