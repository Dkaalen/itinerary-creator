from __future__ import annotations

import importlib
from pathlib import Path

import streamlit as st

from app_modules.calculator_navigation import (
    CALCULATOR_PAGE,
    LOCAL_LIBRARY_PAGE,
    WORKFLOW_PAGE,
    close_calculator_page,
    open_calculator_page,
    open_local_library_page,
)
from app_modules.workflow_config import CALCULATOR_COPY, FLOW_STAGES, STAGE_COPY, STAGE_LABELS
from app_modules.workflow_navigation import session_stage_from_state
from app_modules.workflow_state import ensure_workflow_defaults


CRITICAL_RENDER_MODULES = (
    "app_modules.main_view",
    "app_modules.input_step",
    "app_modules.preview_step",
    "app_modules.picture_step",
    "app_modules.export_page",
    "app_modules.calculator_page",
    "app_modules.local_library_page",
)

CRITICAL_ACTION_MODULES = (
    "app_modules.generation_action",
    "app_modules.project_load_action",
    "app_modules.image_stage_action",
    "app_modules.export_stage_action",
    "app_modules.calculator_download_action",
    "app_modules.saved_project_builder",
    "app_modules.saved_project_update",
    "project_storage.project_browser",
    "app_modules.project_storage_workflow",
    "calculator.workbook_export",
    "parser_modules.parser_main",
    "pdf_exporter_modules.exporter",
    "visual_editor_component.editor_workflow",
)

FRONTEND_ASSETS = (
    "calculator_grid_component/frontend/index.html",
    "calculator_grid_component/frontend/js/calculator_grid_app.js",
    "calculator_grid_component/frontend/js/calculator_grid_render.js",
    "calculator_grid_component/frontend/js/streamlit_bridge.js",
    "calculator_grid_component/frontend/styles/calculator_grid.css",
    "visual_editor_component/frontend/index.html",
    "visual_editor_component/frontend/js/editor_shell.js",
    "visual_editor_component/frontend/js/editor_save_state.js",
    "visual_editor_component/frontend/js/editor_image_tools.js",
    "visual_editor_component/frontend/js/streamlit_bridge.js",
    "visual_editor_component/frontend/styles/editor.css",
)


def test_critical_render_and_action_modules_import() -> None:
    for module_name in (*CRITICAL_RENDER_MODULES, *CRITICAL_ACTION_MODULES):
        assert importlib.import_module(module_name), module_name


def test_critical_workflow_copy_and_stages_are_complete() -> None:
    assert FLOW_STAGES == ("input", "edit", "pictures", "export")
    assert set(STAGE_LABELS) == set(FLOW_STAGES)
    assert set(STAGE_COPY) == set(FLOW_STAGES)

    for stage in FLOW_STAGES:
        copy = STAGE_COPY[stage]
        assert copy["panel_title"].strip()
        assert copy["panel_text"].strip()
        if stage == "input":
            assert copy["headline"].strip()
        else:
            assert copy["subtitle"].strip()

    assert CALCULATOR_COPY["panel_title"].strip()
    assert CALCULATOR_COPY["panel_text"].strip()


def test_app_page_routing_keeps_all_major_surfaces_reachable() -> None:
    state: dict[str, object] = {"app_stage": "input", "itinerary_name": "Oslo Test"}
    ensure_workflow_defaults(state)

    open_calculator_page(state)
    assert state["active_app_page"] == CALCULATOR_PAGE
    assert state["calculator_state"] is not None
    assert session_stage_from_state(state) == "input"

    open_local_library_page(state)
    assert state["active_app_page"] == LOCAL_LIBRARY_PAGE

    close_calculator_page(state)
    assert state["active_app_page"] == WORKFLOW_PAGE


def test_main_view_dispatches_to_every_critical_surface(monkeypatch) -> None:
    import app_modules.main_view as main_view

    calls: list[str] = []

    monkeypatch.setattr(main_view, "render_debug_tools", lambda: calls.append("debug"))
    monkeypatch.setattr(main_view, "render_calculator_page", lambda version: calls.append(f"calculator:{version}"))
    monkeypatch.setattr(main_view, "render_local_library_page", lambda version: calls.append(f"library:{version}"))
    monkeypatch.setattr(main_view, "render_input_page", lambda version: calls.append(f"input:{version}"))
    monkeypatch.setattr(main_view, "render_edit_page", lambda version: calls.append(f"edit:{version}"))
    monkeypatch.setattr(main_view, "render_picture_page", lambda version: calls.append(f"pictures:{version}"))
    monkeypatch.setattr(main_view, "render_export_page", lambda version: calls.append(f"export:{version}"))

    cases = (
        ({"active_app_page": CALCULATOR_PAGE}, "calculator:v"),
        ({"active_app_page": LOCAL_LIBRARY_PAGE}, "library:v"),
        ({"app_stage": "input", "parsed_rows": []}, "input:v"),
        ({"app_stage": "edit", "parsed_rows": [{"day": "Day 1"}], "output_edits": {}}, "edit:v"),
        ({"app_stage": "pictures", "parsed_rows": [{"day": "Day 1"}], "output_edits": {"pictures_added": True}}, "pictures:v"),
        ({"app_stage": "export", "parsed_rows": [{"day": "Day 1"}], "output_edits": {"pictures_added": True}}, "export:v"),
    )

    for state_patch, expected in cases:
        calls.clear()
        main_view.render_app("v", state=dict(state_patch))
        assert expected in calls
        assert "debug" in calls


def test_frontend_assets_required_by_critical_components_exist() -> None:
    for relative_path in FRONTEND_ASSETS:
        path = Path(relative_path)
        assert path.exists(), relative_path
        assert path.read_text(encoding="utf-8").strip(), relative_path
