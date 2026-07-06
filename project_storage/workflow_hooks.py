"""Storage hooks for generated projects, calculator files, and PDF exports."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from typing import Any

from app_modules.project_identity import (
    active_project_id_from_state,
    ensure_active_project_id,
    set_active_project_id,
)
from calculator.calculator_state import CalculatorState
from calculator.state_serialization import calculator_state_to_dict
from project_storage.errors import clear_storage_error, record_storage_error
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
        repository.upsert_itinerary(itinerary_id, name=_state_itinerary_name(state), status="draft")
        version_number = repository.next_version_number(itinerary_id, itinerary_type)
        content = json.dumps(project, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        storage_path = itinerary_snapshot_path(itinerary_id, itinerary_type, version_number)
        _save_versioned_file(
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
    else:
        set_active_project_id(state, itinerary_id)
    itinerary_name = str(metadata.get("itinerary_name") or _state_itinerary_name(state) or "Untitled itinerary")
    itinerary_type = str(project.get("output_brand") or project.get("mode") or "agent")

    try:
        repository.upsert_itinerary(itinerary_id, name=itinerary_name, status=str(metadata.get("status") or "draft"))
        version_number = repository.next_version_number(itinerary_id, itinerary_type)
        content = json.dumps(project, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        storage_path = itinerary_snapshot_path(itinerary_id, itinerary_type, version_number)
        _save_versioned_file(
            repository,
            itinerary_id=itinerary_id,
            version_number=version_number,
            itinerary_type=itinerary_type,
            source_type=source_type,
            payload=project,
            file_type="saved_project_json",
            filename=storage_path.rsplit("/", 1)[-1],
            storage_path=storage_path,
            content=content,
            content_type=PROJECT_JSON_MIME,
        )
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
        _save_unversioned_file(
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
        _save_unversioned_file(
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


def _save_versioned_file(
    repository: Any,
    *,
    itinerary_id: str,
    version_number: int,
    itinerary_type: str,
    source_type: str,
    payload: dict[str, Any],
    file_type: str,
    filename: str,
    storage_path: str,
    content: bytes,
    content_type: str,
) -> None:
    """Save a versioned payload without leaving storage files when DB registration fails."""

    version_id = ""
    repository.upload_file(storage_path, content, content_type=content_type)
    try:
        version = repository.create_version(
            itinerary_id=itinerary_id,
            version_number=version_number,
            itinerary_type=itinerary_type,
            source_type=source_type,
            payload=payload,
        )
        version_id = str(version.get("id") or "")
        repository.register_file(
            itinerary_id=itinerary_id,
            version_id=version_id or None,
            file_type=file_type,
            filename=filename,
            storage_path=storage_path,
        )
    except Exception:
        _best_effort_cleanup(repository, storage_path=storage_path, version_id=version_id)
        raise


def _save_unversioned_file(
    repository: Any,
    *,
    itinerary_id: str,
    file_type: str,
    filename: str,
    storage_path: str,
    content: bytes,
    content_type: str,
) -> None:
    """Save a storage file and remove it if the file record cannot be registered."""

    repository.upload_file(storage_path, content, content_type=content_type)
    try:
        repository.register_file(
            itinerary_id=itinerary_id,
            file_type=file_type,
            filename=filename,
            storage_path=storage_path,
        )
    except Exception:
        _best_effort_cleanup(repository, storage_path=storage_path)
        raise


def _best_effort_cleanup(repository: Any, *, storage_path: str, version_id: str = "") -> None:
    try:
        repository.delete_storage_files([storage_path])
    except Exception:
        pass
    try:
        repository.delete_version(version_id)
    except Exception:
        pass


def _state_itinerary_name(state: MutableMapping[str, Any], fallback: str = "") -> str:
    return " ".join(str(state.get("itinerary_name") or state.get("itinerary_name_input") or fallback or "Untitled itinerary").split())
