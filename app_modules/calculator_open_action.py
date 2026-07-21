"""Apply local Calculator file imports at a safe project boundary."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

from app_modules.calculator_backup_action import CalculatorUploadImport
from app_modules.calculator_restore import restore_calculator_workspace
from app_modules.session_transitions import begin_local_calculator_import


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
