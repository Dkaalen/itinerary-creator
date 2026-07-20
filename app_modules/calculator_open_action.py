"""Apply local Calculator file imports at a safe project boundary."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

from app_modules.calculator_backup_action import CalculatorUploadImport
from app_modules.calculator_session_state import store_calculator_state
from app_modules.calculator_state_keys import (
    CALCULATOR_RETURN_AVAILABLE_KEY,
    CURRENCY_RATES_STATE_KEY,
)
from app_modules.project_session_cleanup import clear_active_cloud_project_session


@dataclass(frozen=True)
class CalculatorOpenNotice:
    """User-facing result of opening one local Calculator file."""

    level: str
    message: str


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

    clear_active_cloud_project_session(session_state)
    session_state.pop(CALCULATOR_RETURN_AVAILABLE_KEY, None)

    if imported.currency_rates:
        rates = {str(code).upper(): float(value) for code, value in imported.currency_rates.items()}
        session_state[CURRENCY_RATES_STATE_KEY] = rates
        for code, value in rates.items():
            session_state[f"calculator_currency_rate_{code}"] = value

    store_calculator_state(session_state, imported.state, sync_name_input=True)
    return _open_notice(imported, filename=filename)


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


__all__ = ["CalculatorOpenNotice", "apply_calculator_upload_import"]
