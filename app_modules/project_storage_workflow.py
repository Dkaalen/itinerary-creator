"""Application workflow hooks for project storage and export persistence."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from typing import Any

import diagnostics

from app_modules.project_identity import (
    active_project_id_from_state,
    ensure_active_project_id,
    project_payload_with_id,
    set_active_project_id,
)
from app_modules.project_storage_error_state import clear_storage_error, record_storage_error
from app_modules.project_storage_runtime import get_project_storage_repository
from app_modules.session_state_keys import (
    ACTIVE_SAVED_PROJECT_KEY,
    ITINERARY_NAME_INPUT_KEY,
    ITINERARY_NAME_KEY,
    OUTPUT_EDITS_KEY,
    PROJECT_STORAGE_LAST_CALCULATOR_FILE_PATH_KEY,
    PROJECT_STORAGE_LAST_CALCULATOR_SNAPSHOT_KEY,
    PROJECT_STORAGE_LAST_PDF_PATH_KEY,
    PROJECT_STORAGE_LAST_SAVED_SNAPSHOT_PATH_KEY,
    REQUESTED_OUTPUT_BRAND_KEY,
)
from calculator.calculator_state import CalculatorState
from calculator.state_serialization import calculator_state_to_dict
from project_storage.file_writer import (
    CALCULATION_XLSX_MIME,
    PDF_MIME,
    PROJECT_JSON_MIME,
    save_unversioned_file,
    save_versioned_file,
)
from project_storage.paths import calculator_workbook_path, itinerary_snapshot_path, pdf_export_path


def save_generated_project_snapshot(state: MutableMapping[str, Any]) -> bool:
    """Persist the active generated itinerary snapshot when storage is configured."""

    project = state.get(ACTIVE_SAVED_PROJECT_KEY)
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
        state[PROJECT_STORAGE_LAST_SAVED_SNAPSHOT_PATH_KEY] = storage_path
        clear_storage_error(state)
        return True
    except Exception as exc:
        diagnostics.warn_exception(
            "project_storage_save",
            "Generated project snapshot could not be saved to cloud storage.",
            exc,
            source="app_modules.project_storage_workflow",
        )
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
        state[ACTIVE_SAVED_PROJECT_KEY] = normalized_project
        state[ITINERARY_NAME_KEY] = itinerary_name
        set_active_project_id(state, itinerary_id)
        state[PROJECT_STORAGE_LAST_SAVED_SNAPSHOT_PATH_KEY] = storage_path
        clear_storage_error(state)
        return True
    except Exception as exc:
        diagnostics.warn_exception(
            "project_storage_save",
            "Project payload snapshot could not be saved to cloud storage.",
            exc,
            source="app_modules.project_storage_workflow",
        )
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
        state[PROJECT_STORAGE_LAST_CALCULATOR_FILE_PATH_KEY] = storage_path
        state[PROJECT_STORAGE_LAST_CALCULATOR_SNAPSHOT_KEY] = {
            **calculator_state_to_dict(calculator_state),
            "currency_rates": dict(currency_rates or {}),
        }
        clear_storage_error(state)
        return True
    except Exception as exc:
        diagnostics.warn_exception(
            "project_storage_save",
            "Calculator workbook could not be saved to cloud storage.",
            exc,
            filename,
            source="app_modules.project_storage_workflow",
        )
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
    output_brand = str((state.get(OUTPUT_EDITS_KEY) or {}).get("output_brand") or state.get(REQUESTED_OUTPUT_BRAND_KEY) or "agent")

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
        state[PROJECT_STORAGE_LAST_PDF_PATH_KEY] = storage_path
        clear_storage_error(state)
        return True
    except Exception as exc:
        diagnostics.warn_exception(
            "project_storage_save",
            "PDF export could not be saved to cloud storage.",
            exc,
            filename,
            source="app_modules.project_storage_workflow",
        )
        record_storage_error(state, exc, action="save")
        return False


def ensure_storage_itinerary(state: MutableMapping[str, Any], *, name: str = "") -> str:
    """Return the current itinerary id, creating one in session state when needed."""

    itinerary_id = ensure_active_project_id(state)
    if name and not state.get(ITINERARY_NAME_KEY):
        state[ITINERARY_NAME_KEY] = name
    return itinerary_id


def _state_itinerary_name(state: MutableMapping[str, Any], fallback: str = "") -> str:
    return " ".join(str(state.get(ITINERARY_NAME_KEY) or state.get(ITINERARY_NAME_INPUT_KEY) or fallback or "Untitled itinerary").split())
