"""Storage hooks for generated projects, calculator files, and PDF exports."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from typing import Any
from app_modules.project_identity import (
    active_project_id_from_state,
    ensure_active_project_id,
    project_payload_with_id,
    set_active_project_id,
)
from calculator.calculator_state import CalculatorState
from calculator.state_serialization import calculator_state_to_dict
from project_storage.errors import clear_storage_error, record_storage_error
from project_storage.file_writer import (
    CALCULATION_XLSX_MIME,
    PDF_MIME,
    PROJECT_JSON_MIME,
    save_unversioned_file,
    save_versioned_file,
)
from project_storage.paths import calculator_workbook_path, itinerary_snapshot_path, pdf_export_path
from project_storage.runtime import get_project_storage_repository


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
        repository.upsert_itinerary(itinerary_id, name=_state_itinerary_name(state), status="draft")
        version_number = repository.next_version_number(itinerary_id, itinerary_type)
        content = json.dumps(project, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        storage_path = itinerary_snapshot_path(itinerary_id, itinerary_type, version_number)
        save_versioned_file(
            repository,
            itinerary_id=itinerary_id,
            version_number=version_number,
            itinerary_type=itinerary_type,
            source_type="generated_itinerary",
            payload=project,
            file_type="generated_itinerary_json",
            filename=storage_path.rsplit("/", 1)[-1],
            storage_path=storage_path,
            content=content,
            content_type=PROJECT_JSON_MIME,
        )
        state["project_storage_last_saved_snapshot_path"] = storage_path
        clear_storage_error(state)
        return True
    except Exception as exc:
        record_storage_error(state, exc, action="save")
        return False


def save_project_payload_snapshot(state: MutableMapping[str, Any], project: dict[str, Any], *, source_type: str = "manual_save") -> bool:
    """Persist a saved-project payload as the latest cloud project version."""

    repository = get_project_storage_repository()
    if repository is None or not isinstance(project, dict):
        return False

    metadata = project.get("metadata") if isinstance(project.get("metadata"), dict) else {}
    itinerary_id = active_project_id_from_state(state) or str(metadata.get("project_id") or "").strip()
    if not itinerary_id:
        itinerary_id = ensure_storage_itinerary(state, name=str(metadata.get("itinerary_name") or ""))
    if not itinerary_id:
        return False

    normalized_project = project_payload_with_id(project, itinerary_id)
    normalized_metadata = normalized_project.get("metadata") if isinstance(normalized_project.get("metadata"), dict) else {}
    itinerary_name = str(normalized_metadata.get("itinerary_name") or _state_itinerary_name(state) or "Untitled itinerary")
    itinerary_type = str(normalized_project.get("output_brand") or normalized_project.get("mode") or "agent")

    try:
        repository.upsert_itinerary(itinerary_id, name=itinerary_name, status=str(normalized_metadata.get("status") or "draft"))
        version_number = repository.next_version_number(itinerary_id, itinerary_type)
        content = json.dumps(normalized_project, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        storage_path = itinerary_snapshot_path(itinerary_id, itinerary_type, version_number)
        save_versioned_file(
            repository,
            itinerary_id=itinerary_id,
            version_number=version_number,
            itinerary_type=itinerary_type,
            source_type=source_type,
            payload=normalized_project,
            file_type="saved_project_json",
            filename=storage_path.rsplit("/", 1)[-1],
            storage_path=storage_path,
            content=content,
            content_type=PROJECT_JSON_MIME,
        )
        state["active_saved_project"] = normalized_project
        state["itinerary_name"] = itinerary_name
        set_active_project_id(state, itinerary_id)
        state["project_storage_last_saved_snapshot_path"] = storage_path
        clear_storage_error(state)
        return True
    except Exception as exc:
        record_storage_error(state, exc, action="save")
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
        save_unversioned_file(
            repository,
            itinerary_id=itinerary_id,
            file_type="calculator_xlsx",
            filename=filename,
            storage_path=storage_path,
            content=content,
            content_type=CALCULATION_XLSX_MIME,
        )
        state["project_storage_last_calculator_file_path"] = storage_path
        state["project_storage_last_calculator_snapshot"] = {
            **calculator_state_to_dict(calculator_state),
            "currency_rates": dict(currency_rates or {}),
        }
        clear_storage_error(state)
        return True
    except Exception as exc:
        record_storage_error(state, exc, action="save")
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
        save_unversioned_file(
            repository,
            itinerary_id=itinerary_id,
            file_type="pdf_export",
            filename=filename,
            storage_path=storage_path,
            content=content,
            content_type=PDF_MIME,
        )
        state["project_storage_last_pdf_path"] = storage_path
        clear_storage_error(state)
        return True
    except Exception as exc:
        record_storage_error(state, exc, action="save")
        return False


def ensure_storage_itinerary(state: MutableMapping[str, Any], *, name: str = "") -> str:
    """Return the current itinerary id, creating one in session state when needed."""

    itinerary_id = ensure_active_project_id(state)
    if name and not state.get("itinerary_name"):
        state["itinerary_name"] = name
    return itinerary_id


def _state_itinerary_name(state: MutableMapping[str, Any], fallback: str = "") -> str:
    return " ".join(str(state.get("itinerary_name") or state.get("itinerary_name_input") or fallback or "Untitled itinerary").split())
