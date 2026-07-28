from __future__ import annotations

from app_modules.project_browser_controls import ProjectBrowserQuery
from app_modules.performance_telemetry import begin_rerun, trace_events
from app_modules.project_browser_management_actions import apply_delete_projects
from app_modules.project_browser_paging import ProjectPage
from app_modules.project_browser_state import (
    bump_project_table_revision,
    consume_bulk_action,
    remember_bulk_action,
    remember_project_explorer_event,
    remember_selected_projects,
    selected_project_ids,
)
from project_storage.delete_result import ProjectDeleteResult
from project_storage.project_results import (
    ProjectBulkPurgeResult,
    ProjectPurgeItemResult,
)
from tests.support.streamlit_stub import SessionState


def test_legacy_capability_uses_basic_browser_without_attempting_management_query(monkeypatch) -> None:
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
    management_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        project_browser_ui,
        "list_cloud_project_explorer_page",
        lambda **kwargs: management_calls.append(kwargs)
        or (_ for _ in ()).throw(RuntimeError("management query must not run")),
    )
    monkeypatch.setattr(project_browser_ui, "list_cloud_itinerary_page", lambda **kwargs: legacy_page)

    page, management_ready = project_browser_ui._load_project_page(
        ProjectBrowserQuery(),
        page_index=0,
    )

    assert page is legacy_page
    assert management_ready is False
    assert management_calls == []


def test_management_query_failure_does_not_issue_a_hidden_legacy_fallback(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_ui
    from project_storage.capabilities import ProjectStorageCapabilities

    st.session_state = SessionState()
    warnings: list[str] = []
    legacy_calls: list[bool] = []
    monkeypatch.setattr(
        project_browser_ui,
        "list_cloud_project_explorer_page",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("network unavailable")),
    )
    monkeypatch.setattr(
        project_browser_ui,
        "list_cloud_itinerary_page",
        lambda **kwargs: legacy_calls.append(True),
    )
    monkeypatch.setattr(st, "warning", lambda message: warnings.append(str(message)))

    page, management_ready = project_browser_ui._load_project_page(
        ProjectBrowserQuery(),
        page_index=0,
        capabilities=ProjectStorageCapabilities.full(),
    )

    assert page is None
    assert management_ready is True
    assert legacy_calls == []
    assert warnings


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




def test_delete_telemetry_correlates_requested_and_partial_result_ids(monkeypatch) -> None:
    from app_modules import project_browser_management_actions

    state = SessionState()
    begin_rerun(state)
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

    assert apply_delete_projects(state, ("project-1", "project-2")) is False

    events = trace_events(state)
    started = next(item for item in events if item["event"] == "project_delete_started")
    completed = next(item for item in events if item["event"] == "project_delete_completed")
    assert started["project_ids"] == ["project-1", "project-2"]
    assert completed["deleted_project_ids"] == ["project-1"]
    assert completed["incomplete_project_ids"] == ["project-2"]
    assert completed["outcome"] == "partial"
    assert completed["operation_id"] == started["operation_id"]
    assert selected_project_ids(state) == ("project-2",)



def test_delete_confirmation_token_is_exact_current_and_one_use() -> None:
    state = SessionState()
    remember_selected_projects(state, ("project-1", "project-2"))
    token = remember_bulk_action(
        state,
        action="delete",
        project_ids=("project-1", "project-2"),
        project_names=("Norway", "Iceland"),
    )

    consumed = consume_bulk_action(
        state,
        token=token,
        project_ids=("project-1", "project-2"),
        list_revision=0,
    )

    assert consumed is not None
    assert consumed.project_ids == ("project-1", "project-2")
    assert consume_bulk_action(
        state,
        token=token,
        project_ids=("project-1", "project-2"),
        list_revision=0,
    ) is None


def test_delete_confirmation_rejects_changed_selection_and_list_revision() -> None:
    state = SessionState()
    remember_selected_projects(state, ("project-1", "project-2"))
    token = remember_bulk_action(
        state,
        action="delete",
        project_ids=("project-1", "project-2"),
    )
    remember_selected_projects(state, ("project-1",))

    assert consume_bulk_action(
        state,
        token=token,
        project_ids=("project-1", "project-2"),
        list_revision=0,
    ) is None

    remember_selected_projects(state, ("project-1", "project-2"))
    bump_project_table_revision(state)
    assert consume_bulk_action(
        state,
        token=token,
        project_ids=("project-1", "project-2"),
        list_revision=0,
    ) is None


def test_project_explorer_component_event_is_processed_once() -> None:
    state = SessionState()

    assert remember_project_explorer_event(state, "event-1") is True
    assert remember_project_explorer_event(state, "event-1") is False
    assert remember_project_explorer_event(state, "event-2") is True


def test_complete_delete_clears_selection_but_partial_delete_keeps_failed_ids(monkeypatch) -> None:
    from app_modules import project_browser_management_actions

    state = SessionState()
    remember_selected_projects(state, ("project-1", "project-2"))
    partial = ProjectBulkPurgeResult(
        items=(
            ProjectPurgeItemResult(
                project_id="project-1",
                result=ProjectDeleteResult(
                    itinerary_id="project-1",
                    record_deleted=True,
                    storage_files_deleted=True,
                ),
            ),
            ProjectPurgeItemResult(project_id="project-2", error="storage failed"),
        )
    )
    monkeypatch.setattr(
        project_browser_management_actions,
        "permanently_delete_cloud_projects",
        lambda *args, **kwargs: partial,
    )

    assert apply_delete_projects(state, ("project-1", "project-2")) is False
    assert selected_project_ids(state) == ("project-2",)

    complete = ProjectBulkPurgeResult(
        items=(
            ProjectPurgeItemResult(
                project_id="project-2",
                result=ProjectDeleteResult(
                    itinerary_id="project-2",
                    record_deleted=True,
                    storage_files_deleted=True,
                ),
            ),
        )
    )
    monkeypatch.setattr(
        project_browser_management_actions,
        "permanently_delete_cloud_projects",
        lambda *args, **kwargs: complete,
    )

    assert apply_delete_projects(state, ("project-2",)) is True
    assert selected_project_ids(state) == ()


def test_confirmed_delete_passes_the_raw_one_use_token_to_the_delete_owner(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_bulk_ui
    from app_modules.project_browser_state import remember_bulk_action, remember_selected_projects

    st.session_state = SessionState()
    remember_selected_projects(st.session_state, ("project-1", "project-2"))
    token = remember_bulk_action(
        st.session_state,
        action="delete",
        project_ids=("project-1", "project-2"),
        project_names=("Norway", "Iceland"),
    )
    calls: list[tuple[tuple[str, ...], str]] = []
    monkeypatch.setattr(
        st,
        "button",
        lambda label, *args, **kwargs: label == "Delete permanently",
    )
    monkeypatch.setattr(st, "rerun", lambda: None)
    monkeypatch.setattr(
        project_browser_bulk_ui,
        "apply_delete_projects",
        lambda state, project_ids, *, confirmation_token: calls.append(
            (tuple(project_ids), confirmation_token)
        ),
    )

    rendered = project_browser_bulk_ui.render_pending_project_action_confirmation()

    assert rendered is True
    assert calls == [(('project-1', 'project-2'), token)]
