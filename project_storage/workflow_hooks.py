"""Storage hooks for generated projects, calculator files, and PDF exports."""

from __future__ import annotations

import json
import uuid
from collections.abc import MutableMapping
from typing import Any

from calculator.calculator_state import CalculatorState
from calculator.state_serialization import calculator_state_to_dict
from project_storage.paths import calculator_workbook_path, itinerary_snapshot_path, pdf_export_path
from project_storage.runtime import get_project_storage_repository

CALCULATION_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PROJECT_JSON_MIME = "application/json"
PDF_MIME = "application/pdf"


def save_generated_project_snapshot(state: MutableMapping[str, Any]) -> bool:
    """Persist the active generated itinerary snapshot when storage is configured."""

    project = state.get("active_saved_project")
    if not isinstance(project, dict):
        return False
    itinerary_id = ensure_storage_itinerary(state, name=str(project.get("metadata", {}).get("itinerary_name") or ""))
    if not itinerary_id:
        return False
    itinerary_type = str(project.get("output_brand") or project.get("mode") or "agent")
    repository = get_project_storage_repository()
    if repository is None:
        return False

    try:
        version_number = repository.next_version_number(itinerary_id, itinerary_type)
        repository.upsert_itinerary(itinerary_id, name=_state_itinerary_name(state), status="draft")
        version = repository.create_version(
            itinerary_id=itinerary_id,
            version_number=version_number,
            itinerary_type=itinerary_type,
            source_type="generated_itinerary",
            payload=project,
        )
        content = json.dumps(project, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        storage_path = itinerary_snapshot_path(itinerary_id, itinerary_type, version_number)
        repository.upload_file(storage_path, content, content_type=PROJECT_JSON_MIME)
        repository.register_file(
            itinerary_id=itinerary_id,
            version_id=str(version.get("id") or "") or None,
            file_type="generated_itinerary_json",
            filename=storage_path.rsplit("/", 1)[-1],
            storage_path=storage_path,
        )
        state["project_storage_last_saved_snapshot_path"] = storage_path
        state.pop("project_storage_last_error", None)
        return True
    except Exception as exc:
        _record_storage_error(state, exc)
        return False


def save_calculation_workbook(
    state: MutableMapping[str, Any],
    calculator_state: CalculatorState,
    *,
    content: bytes,
    filename: str,
    currency_rates: dict[str, float] | None = None,
) -> bool:
    """Persist a calculator workbook file under the current itinerary id."""

    repository = get_project_storage_repository()
    if repository is None:
        return False
    itinerary_id = ensure_storage_itinerary(state, name=calculator_state.itinerary_name)
    if not itinerary_id:
        return False

    try:
        repository.upsert_itinerary(itinerary_id, name=_state_itinerary_name(state, calculator_state.itinerary_name), status="draft")
        storage_path = calculator_workbook_path(itinerary_id, filename)
        repository.upload_file(storage_path, content, content_type=CALCULATION_XLSX_MIME)
        repository.register_file(
            itinerary_id=itinerary_id,
            file_type="calculator_xlsx",
            filename=filename,
            storage_path=storage_path,
        )
        state["project_storage_last_calculator_file_path"] = storage_path
        state["project_storage_last_calculator_snapshot"] = {
            **calculator_state_to_dict(calculator_state),
            "currency_rates": dict(currency_rates or {}),
        }
        state.pop("project_storage_last_error", None)
        return True
    except Exception as exc:
        _record_storage_error(state, exc)
        return False


def save_pdf_export(state: MutableMapping[str, Any], *, content: bytes, filename: str) -> bool:
    """Persist a generated PDF under the current itinerary id."""

    repository = get_project_storage_repository()
    if repository is None:
        return False
    itinerary_id = ensure_storage_itinerary(state, name=_state_itinerary_name(state))
    if not itinerary_id:
        return False
    output_brand = str((state.get("output_edits") or {}).get("output_brand") or state.get("requested_output_brand") or "agent")

    try:
        repository.upsert_itinerary(itinerary_id, name=_state_itinerary_name(state), status="draft")
        storage_path = pdf_export_path(itinerary_id, output_brand, filename)
        repository.upload_file(storage_path, content, content_type=PDF_MIME)
        repository.register_file(
            itinerary_id=itinerary_id,
            file_type="pdf_export",
            filename=filename,
            storage_path=storage_path,
        )
        state["project_storage_last_pdf_path"] = storage_path
        state.pop("project_storage_last_error", None)
        return True
    except Exception as exc:
        _record_storage_error(state, exc)
        return False


def ensure_storage_itinerary(state: MutableMapping[str, Any], *, name: str = "") -> str:
    """Return the current itinerary id, creating one in session state when needed."""

    existing = str(state.get("active_project_storage_id") or state.get("active_saved_project_id") or "").strip()
    if existing:
        state["active_project_storage_id"] = existing
        return existing
    generated = str(uuid.uuid4())
    state["active_project_storage_id"] = generated
    if name and not state.get("itinerary_name"):
        state["itinerary_name"] = name
    return generated


def _state_itinerary_name(state: MutableMapping[str, Any], fallback: str = "") -> str:
    return " ".join(str(state.get("itinerary_name") or state.get("itinerary_name_input") or fallback or "Untitled itinerary").split())


def _record_storage_error(state: MutableMapping[str, Any], exc: Exception) -> None:
    state["project_storage_last_error"] = str(exc)
