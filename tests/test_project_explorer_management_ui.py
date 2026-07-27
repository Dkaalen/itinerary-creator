from __future__ import annotations

from app_modules.project_browser_controls import ProjectBrowserQuery
from app_modules.project_browser_management_actions import (
    apply_move_to_trash,
    apply_permanent_purge,
    apply_restore_from_trash,
)
from app_modules.project_browser_paging import ProjectPage
from project_storage.delete_result import ProjectDeleteResult
from project_storage.project_results import (
    ProjectBulkMutationFailure,
    ProjectBulkMutationResult,
    ProjectBulkPurgeResult,
    ProjectPurgeItemResult,
)
from tests.support.streamlit_stub import SessionState


def test_management_page_falls_back_to_basic_browser_before_schema_migration(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_ui

    st.session_state = SessionState()
    legacy_page = ProjectPage(
        projects=({"id": "project-1", "name": "Norway"},),
        page_index=0,
        page_size=25,
        has_previous=False,
        has_next=False,
    )
    monkeypatch.setattr(
        project_browser_ui,
        "list_cloud_project_explorer_page",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("migration missing")),
    )
    monkeypatch.setattr(project_browser_ui, "list_cloud_itinerary_page", lambda **kwargs: legacy_page)

    page, management_ready = project_browser_ui._load_project_page(
        ProjectBrowserQuery(),
        page_index=0,
    )

    assert page is legacy_page
    assert management_ready is False


def test_management_page_does_not_hide_missing_schema_for_trash(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_ui

    st.session_state = SessionState()
    errors: list[str] = []
    monkeypatch.setattr(
        project_browser_ui,
        "list_cloud_project_explorer_page",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("migration missing")),
    )
    monkeypatch.setattr(st, "error", lambda message: errors.append(str(message)))

    page, management_ready = project_browser_ui._load_project_page(
        ProjectBrowserQuery(view="trash", sort="trash_recent"),
        page_index=0,
    )

    assert page is None
    assert management_ready is False
    assert errors and "migration" in errors[0].casefold()


def test_calculator_files_are_not_queried_until_explicitly_shown(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_calculation_files

    st.session_state = SessionState()
    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        project_browser_calculation_files,
        "list_cloud_calculation_files",
        lambda project_id, limit: calls.append((project_id, limit)) or (),
    )

    project_browser_calculation_files.render_calculation_files("project-1")

    assert calls == []

    st.session_state["cloud_calculator_files_visible_project-1"] = True
    project_browser_calculation_files.render_calculation_files("project-1")

    assert calls == [("project-1", 8)]


def test_move_to_trash_detaches_active_cloud_identity_but_keeps_workspace(monkeypatch) -> None:
    from app_modules import project_browser_management_actions

    state = SessionState(
        {
            "active_saved_project_id": "project-1",
            "active_project_storage_id": "project-1",
            "active_saved_project": {"metadata": {"project_id": "project-1"}},
            "active_project_cloud_persisted": True,
            "parsed_rows": [{"title": "Keep this itinerary in memory"}],
        }
    )
    result = ProjectBulkMutationResult(
        requested_ids=("project-1",),
        affected_ids=("project-1",),
    )
    monkeypatch.setattr(project_browser_management_actions, "move_cloud_projects_to_trash", lambda *a, **k: result)

    completed = apply_move_to_trash(
        state,
        ("project-1",),
        actor_slug="dennis",
    )

    assert completed is True
    assert "active_saved_project_id" not in state
    assert "active_project_storage_id" not in state
    assert state["parsed_rows"] == [{"title": "Keep this itinerary in memory"}]
    assert "unsaved work" in state["project_storage_browser_warning"].casefold()


def test_partial_bulk_update_reports_the_unmodified_selection(monkeypatch) -> None:
    from app_modules import project_browser_management_actions

    state = SessionState()
    result = ProjectBulkMutationResult(
        requested_ids=("project-1", "project-2"),
        affected_ids=("project-1",),
        failures=(
            ProjectBulkMutationFailure(project_ids=("project-2",), error="network unavailable"),
        ),
    )
    monkeypatch.setattr(
        project_browser_management_actions,
        "restore_cloud_projects_from_trash",
        lambda *args, **kwargs: result,
    )

    completed = apply_restore_from_trash(
        state,
        ("project-1", "project-2"),
        actor_slug="vipin",
    )

    assert completed is False
    assert state["project_storage_browser_success"] == "Restored 1 project."
    assert "1 selected project" in state["project_storage_browser_warning"]


def test_permanent_purge_preserves_retry_warning_for_incomplete_cleanup(monkeypatch) -> None:
    from app_modules import project_browser_management_actions

    state = SessionState()
    result = ProjectBulkPurgeResult(
        items=(
            ProjectPurgeItemResult(
                project_id="project-1",
                result=ProjectDeleteResult(
                    itinerary_id="project-1",
                    record_deleted=True,
                    storage_files_deleted=True,
                ),
            ),
            ProjectPurgeItemResult(project_id="project-2", error="database unavailable"),
        )
    )
    monkeypatch.setattr(
        project_browser_management_actions,
        "permanently_delete_cloud_projects",
        lambda *args, **kwargs: result,
    )

    completed = apply_permanent_purge(state, ("project-1", "project-2"))

    assert completed is False
    assert state["project_storage_browser_success"] == "Permanently deleted 1 project."
    assert "1 selected project" in state["project_storage_browser_warning"]
