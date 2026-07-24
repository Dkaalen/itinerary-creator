from __future__ import annotations

import ast
from pathlib import Path

from project_storage.project_browser import (
    delete_itinerary,
    download_project_file,
    list_calculation_files,
    list_itineraries,
    load_latest_project_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_project_storage_package_has_no_application_or_streamlit_dependency() -> None:
    offenders: list[str] = []
    for path in sorted((ROOT / "project_storage").glob("*.py")):
        forbidden = _import_roots(path) & {"app_modules", "streamlit"}
        if forbidden:
            offenders.append(f"{path.relative_to(ROOT)}:{','.join(sorted(forbidden))}")

    assert offenders == []
    assert not (ROOT / "project_storage" / "workflow_hooks.py").exists()
    assert not (ROOT / "project_storage" / "runtime.py").exists()


def test_application_layer_owns_runtime_paging_and_session_mutation() -> None:
    service = (ROOT / "app_modules" / "project_storage_service.py").read_text(encoding="utf-8")
    workflow = (ROOT / "app_modules" / "project_storage_workflow.py").read_text(encoding="utf-8")
    runtime = (ROOT / "app_modules" / "project_storage_runtime.py").read_text(encoding="utf-8")
    error_state = (ROOT / "app_modules" / "project_storage_error_state.py").read_text(encoding="utf-8")

    assert "build_project_page" in service
    assert "get_project_storage_repository" in service
    assert "ensure_active_project_id" in workflow
    assert "session_state_keys" in workflow
    assert "import streamlit as st" in runtime
    assert "record_failed_save" in error_state


def test_repository_browser_operations_are_pure_and_repository_driven() -> None:
    calls: list[tuple[str, object]] = []

    class Repository:
        def list_itineraries(self, **kwargs):
            calls.append(("list_itineraries", kwargs))
            return [{"id": "project-1"}]

        def list_files(self, itinerary_id, **kwargs):
            calls.append(("list_files", (itinerary_id, kwargs)))
            return [{"id": "file-1"}]

        def download_file(self, storage_path):
            calls.append(("download_file", storage_path))
            return b"payload"

        def delete_itinerary(self, itinerary_id):
            calls.append(("delete_itinerary", itinerary_id))
            return "deleted"

        def latest_version(self, itinerary_id):
            calls.append(("latest_version", itinerary_id))
            return {"payload": {"metadata": {"project_id": itinerary_id}}}

    repository = Repository()

    assert list_itineraries(repository, limit=2, search="Norway", offset=4, sort="name") == ({"id": "project-1"},)
    assert list_calculation_files(repository, "project-1", limit=3) == ({"id": "file-1"},)
    assert download_project_file(repository, "path/file.json") == b"payload"
    assert delete_itinerary(repository, "project-1") == "deleted"
    assert load_latest_project_payload(repository, "project-1") == {"metadata": {"project_id": "project-1"}}
    assert calls == [
        ("list_itineraries", {"limit": 2, "search": "Norway", "offset": 4, "sort": "name"}),
        ("list_files", ("project-1", {"file_type": "calculator_xlsx", "limit": 3})),
        ("download_file", "path/file.json"),
        ("delete_itinerary", "project-1"),
        ("latest_version", "project-1"),
    ]
