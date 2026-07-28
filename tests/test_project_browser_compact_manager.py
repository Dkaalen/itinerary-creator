from __future__ import annotations

from app_modules.project_browser_controls import ProjectBrowserQuery
from app_modules.project_browser_list_ui import (
    ProjectTableSelection,
    project_id_from_table_event,
    project_ids_from_table_event,
    project_table_rows,
)
from app_modules.project_browser_paging import PROJECT_PAGE_SIZE, build_counted_project_page, build_project_page
from app_modules.project_browser_state import (
    browser_page_index,
    remember_delete_candidate,
    remember_selected_project,
    selected_project_id,
    set_browser_page_index,
    sync_project_query,
)
from app_modules.project_storage_service import list_cloud_itinerary_page
from project_storage.capabilities import ProjectStorageCapabilities
from project_storage.project_results import ProjectListResult
from project_storage.repository import _project_order


def test_project_page_keeps_twenty_five_rows_and_one_row_lookahead() -> None:
    rows = tuple({"id": f"project-{index}"} for index in range(PROJECT_PAGE_SIZE + 1))

    page = build_project_page(rows, page_index=2)

    assert len(page.projects) == PROJECT_PAGE_SIZE
    assert page.page_index == 2
    assert page.number == 3
    assert page.has_previous is True
    assert page.has_next is True


def test_counted_page_reports_exact_range_and_page_count() -> None:
    page = build_counted_project_page(
        ProjectListResult(
            projects=tuple({"id": f"project-{index}"} for index in range(22)),
            total_count=47,
        ),
        page_index=1,
        page_size=25,
    )

    assert page.first_item_number == 26
    assert page.last_item_number == 47
    assert page.total_pages == 2
    assert page.last_page_index == 1
    assert page.has_previous is True
    assert page.has_next is False



def test_counted_empty_page_recovers_directly_to_last_valid_page() -> None:
    page = build_counted_project_page(
        ProjectListResult(projects=(), total_count=26),
        page_index=4,
        page_size=25,
    )

    assert page.projects == ()
    assert page.has_previous is True
    assert page.last_page_index == 1

def test_cloud_page_uses_server_offset_sort_and_bounded_limit(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Repository:
        def list_itineraries(self, **kwargs):
            calls.append(kwargs)
            return [{"id": f"project-{index}"} for index in range(26)]

    monkeypatch.setattr("app_modules.project_storage_service.get_project_storage_repository", lambda: Repository())

    page = list_cloud_itinerary_page(page_index=3, page_size=25, search="Norway", sort="name")

    assert calls == [{"limit": 26, "search": "Norway", "offset": 75, "sort": "name"}]
    assert len(page.projects) == 25
    assert page.has_next is True


def test_query_change_resets_page_but_preserves_durable_selection() -> None:
    state: dict[str, object] = {}
    set_browser_page_index(state, 4)
    remember_selected_project(state, "project-4")
    remember_delete_candidate(state, project_id="project-4", name="Norway")

    changed = sync_project_query(state, search="Iceland", sort="recent")

    assert changed is True
    assert browser_page_index(state) == 0
    assert selected_project_id(state) == "project-4"
    assert "open_project_delete_candidate_id" not in state


def test_unchanged_query_preserves_page_and_selection() -> None:
    state: dict[str, object] = {}
    sync_project_query(state, search="Norway", sort="recent")
    set_browser_page_index(state, 2)
    remember_selected_project(state, "project-2")

    changed = sync_project_query(state, search="  Norway  ", sort="RECENT")

    assert changed is False
    assert browser_page_index(state) == 2
    assert selected_project_id(state) == "project-2"


def test_repository_sort_values_are_allowlisted() -> None:
    assert _project_order("recent") == "updated_at.desc,id.asc"
    assert _project_order("oldest") == "updated_at.asc,id.asc"
    assert _project_order("name") == "name.asc,id.asc"
    assert _project_order("created_recent") == "created_at.desc,id.asc"
    assert _project_order("created_oldest") == "created_at.asc,id.asc"
    assert _project_order("unsupported") == "updated_at.desc,id.asc"


def test_repository_list_query_applies_offset_search_and_allowlisted_sort() -> None:
    from project_storage.config import SupabaseStorageConfig
    from project_storage.repository import ProjectStorageRepository

    class Client:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        def rest_get(self, table: str, params: dict[str, str]):
            self.calls.append((table, params))
            return []

    client = Client()
    repository = ProjectStorageRepository(
        SupabaseStorageConfig(url="https://abc.supabase.co", secret_key="secret", bucket="files"),
        client=client,
    )

    repository.list_itineraries(limit=13, search="Nor_way", offset=24, sort="name")

    assert client.calls == [
        (
            "itineraries",
            {
                "select": "id,name,status,created_at,updated_at",
                "order": "name.asc,id.asc",
                "limit": "13",
                "offset": "24",
                "name": "ilike.*Norway*",
            },
        )
    ]

    repository.list_itineraries(limit=26, search="", offset=0, sort="created_recent")

    assert client.calls[-1][1]["order"] == "created_at.desc,id.asc"


def test_manager_renders_one_bounded_page_and_one_selected_detail(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_ui
    from app_modules.project_browser_paging import ProjectPage
    from tests.support.streamlit_stub import SessionState

    st.session_state = SessionState({
        "open_project_delete_candidate_id": "project-1",
        "open_project_rename_candidate_id": "project-1",
        "open_project_unsaved_open_candidate_id": "project-1",
    })
    page = ProjectPage(
        projects=(
            {"id": "project-1", "name": "Norway", "status": "draft"},
            {"id": "project-2", "name": "Iceland", "status": "draft"},
        ),
        page_index=0,
        page_size=25,
        has_previous=False,
        has_next=False,
    )
    page_calls: list[dict[str, object]] = []
    table_calls: list[dict[str, object]] = []
    detail_calls: list[tuple[dict[str, object] | None, ProjectBrowserQuery]] = []
    query = ProjectBrowserQuery()

    def fake_page(**kwargs):
        page_calls.append(kwargs)
        return page

    def fake_table(table_page, **kwargs):
        table_calls.append({"page": table_page, **kwargs})
        return ProjectTableSelection(
            project_ids=("project-2",),
            projects=({"id": "project-2", "name": "Iceland"},),
            action="commit_selection",
            event_id="event-1",
            list_revision=0,
        )

    def fake_detail(project, *, query):
        detail_calls.append((project, query))

    monkeypatch.setattr(project_browser_ui, "render_project_browser_controls", lambda capabilities: query)
    monkeypatch.setattr(
        project_browser_ui,
        "cloud_project_capabilities",
        lambda: ProjectStorageCapabilities.full(),
    )
    monkeypatch.setattr(project_browser_ui, "list_cloud_project_explorer_page", fake_page)
    monkeypatch.setattr(project_browser_ui, "render_project_table", fake_table)
    monkeypatch.setattr(project_browser_ui, "render_selected_project_panel", fake_detail)

    project_browser_ui._render_cloud_project_browser()

    assert page_calls == [{
        "page_index": 0,
        "page_size": 25,
        "search": "",
        "sort": "recent",
        "owner_slug": "",
        "folder_name": "",
    }]
    assert table_calls == [{
        "page": page,
        "selected_project_id": "",
        "selected_project_ids": (),
        "selected_projects": (),
        "active_project_id": "",
        "search": "",
        "sort": "recent",
        "owner_slug": "",
        "folder_name": "",
    }]
    assert detail_calls == [(page.projects[1], query)]
    assert st.session_state["open_project_selected_project_id"] == "project-2"
    assert "open_project_delete_candidate_id" not in st.session_state
    assert "open_project_rename_candidate_id" not in st.session_state
    assert "open_project_unsaved_open_candidate_id" not in st.session_state


def test_open_request_selects_target_before_direct_open(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_actions
    from tests.support.streamlit_stub import SessionState

    st.session_state = SessionState()
    opened: list[str] = []
    monkeypatch.setattr(project_browser_actions, "open_cloud_project", opened.append)

    project_browser_actions.request_open_cloud_project("project-2")

    assert st.session_state["open_project_selected_project_id"] == "project-2"
    assert opened == ["project-2"]


def test_open_request_requires_confirmation_for_unsaved_local_calculator(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_actions
    from calculator.calculator_state import add_row, create_calculator_state
    from calculator.row_model import CalculatorRow
    from tests.support.streamlit_stub import SessionState

    st.session_state = SessionState(
        {
            "calculator_state": add_row(
                create_calculator_state("Local workbook"),
                CalculatorRow(row_id="1", travel_element="Unsaved hotel", gross_price_per_unit=100, units=1),
            )
        }
    )
    opened: list[str] = []
    reruns: list[bool] = []
    monkeypatch.setattr(project_browser_actions, "open_cloud_project", opened.append)
    monkeypatch.setattr(st, "rerun", lambda: reruns.append(True))

    project_browser_actions.request_open_cloud_project("project-2")

    assert st.session_state["open_project_selected_project_id"] == "project-2"
    assert st.session_state["open_project_unsaved_open_candidate_id"] == "project-2"
    assert opened == []
    assert reruns == [True]


def test_open_request_ignores_empty_local_calculator_starter_rows(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_actions
    from calculator.calculator_state import add_row, create_calculator_state
    from calculator.row_model import CalculatorRow
    from tests.support.streamlit_stub import SessionState

    st.session_state = SessionState(
        {
            "calculator_state": add_row(
                create_calculator_state(""),
                CalculatorRow(row_id="1"),
            )
        }
    )
    opened: list[str] = []
    monkeypatch.setattr(project_browser_actions, "open_cloud_project", opened.append)

    project_browser_actions.request_open_cloud_project("project-2")

    assert opened == ["project-2"]
    assert "open_project_unsaved_open_candidate_id" not in st.session_state


def test_project_table_rows_include_durable_ids_and_display_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        "app_modules.project_browser_list_ui.friendly_storage_time",
        lambda value: f"friendly:{value}",
    )
    page = build_project_page(
        [
            {
                "id": "durable-project-id",
                "name": "Norway Winter",
                "owner_slug": "dennis",
                "folder_name": "ITIN-2020",
                "last_saved_at": "2026-07-27T14:30:00Z",
            }
        ],
        page_index=0,
    )

    rows = project_table_rows(page, active_project_id="durable-project-id")

    assert rows == ({
        "id": "durable-project-id",
        "name": "Norway Winter",
        "owner": "Dennis",
        "folder": "ITIN-2020",
        "last_saved": "friendly:2026-07-27T14:30:00Z",
        "is_open": True,
    },)


def test_project_table_event_accepts_only_explicit_durable_ids() -> None:
    event = {
        "event_id": "event-1",
        "action": "commit_selection",
        "list_revision": 4,
        "selected_project_ids": ["project-2", "project-1", "project-2"],
        "selected_projects": [
            {"id": "project-1", "name": "Norway"},
            {"id": "project-2", "name": "Iceland"},
        ],
    }

    assert project_id_from_table_event(event) == "project-2"
    assert project_ids_from_table_event(event) == ("project-2", "project-1")
    assert project_ids_from_table_event({"selection": {"rows": [1]}}) == ()


def test_project_table_event_rejects_invalid_page_delta() -> None:
    from app_modules.project_browser_list_ui import project_table_selection_from_event

    selection = project_table_selection_from_event({
        "event_id": "event-2",
        "action": "page",
        "list_revision": 2,
        "page_delta": 99,
        "selected_project_ids": ["project-1"],
    })

    assert selection.project_ids == ("project-1",)
    assert selection.page_delta == 0


def test_reselecting_same_project_preserves_pending_confirmation(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_ui
    from tests.support.streamlit_stub import SessionState

    st.session_state = SessionState(
        {
            "open_project_selected_project_id": "project-1",
            "open_project_rename_candidate_id": "project-1",
            "open_project_unsaved_open_candidate_id": "project-1",
        }
    )

    from app_modules.project_browser_state import remember_selected_projects

    remember_selected_projects(st.session_state, ("project-1",))

    assert st.session_state["open_project_rename_candidate_id"] == "project-1"
    assert st.session_state["open_project_unsaved_open_candidate_id"] == "project-1"

    project_browser_ui._select_project("project-2")

    assert st.session_state["open_project_selected_project_id"] == "project-2"
    assert "open_project_rename_candidate_id" not in st.session_state
    assert "open_project_unsaved_open_candidate_id" not in st.session_state
