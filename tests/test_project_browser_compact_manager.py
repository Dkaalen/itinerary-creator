from __future__ import annotations

from app_modules.project_browser_paging import PROJECT_PAGE_SIZE, build_project_page
from app_modules.project_browser_state import (
    browser_page_index,
    remember_delete_candidate,
    remember_selected_project,
    selected_project_id,
    set_browser_page_index,
    sync_project_query,
)
from project_storage.project_browser import list_cloud_itinerary_page
from project_storage.repository import _project_order


def test_project_page_keeps_twelve_rows_and_one_row_lookahead() -> None:
    rows = tuple({"id": f"project-{index}"} for index in range(PROJECT_PAGE_SIZE + 1))

    page = build_project_page(rows, page_index=2)

    assert len(page.projects) == PROJECT_PAGE_SIZE
    assert page.page_index == 2
    assert page.number == 3
    assert page.has_previous is True
    assert page.has_next is True


def test_cloud_page_uses_server_offset_sort_and_bounded_limit(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Repository:
        def list_itineraries(self, **kwargs):
            calls.append(kwargs)
            return [{"id": f"project-{index}"} for index in range(13)]

    monkeypatch.setattr("project_storage.project_browser.get_project_storage_repository", lambda: Repository())

    page = list_cloud_itinerary_page(page_index=3, page_size=12, search="Norway", sort="name")

    assert calls == [{"limit": 13, "search": "Norway", "offset": 36, "sort": "name"}]
    assert len(page.projects) == 12
    assert page.has_next is True


def test_query_change_resets_page_selection_and_open_actions() -> None:
    state: dict[str, object] = {}
    set_browser_page_index(state, 4)
    remember_selected_project(state, "project-4")
    remember_delete_candidate(state, project_id="project-4", name="Norway")

    changed = sync_project_query(state, search="Iceland", sort="recent")

    assert changed is True
    assert browser_page_index(state) == 0
    assert selected_project_id(state) == ""
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
    assert _project_order("recent") == "updated_at.desc"
    assert _project_order("oldest") == "updated_at.asc"
    assert _project_order("name") == "name.asc"
    assert _project_order("unsupported") == "updated_at.desc"


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
                "order": "name.asc",
                "limit": "13",
                "offset": "24",
                "name": "ilike.*Norway*",
            },
        )
    ]


def test_manager_renders_one_bounded_page_and_one_selected_detail(monkeypatch) -> None:
    import streamlit as st
    from app_modules import project_browser_ui
    from app_modules.project_browser_paging import ProjectPage
    from tests.support.streamlit_stub import SessionState

    st.session_state = SessionState()
    page = ProjectPage(
        projects=(
            {"id": "project-1", "name": "Norway", "status": "draft"},
            {"id": "project-2", "name": "Iceland", "status": "draft"},
        ),
        page_index=0,
        page_size=12,
        has_previous=False,
        has_next=False,
    )
    page_calls: list[dict[str, object]] = []
    list_calls: list[ProjectPage] = []
    detail_calls: list[dict[str, object] | None] = []

    def fake_page(**kwargs):
        page_calls.append(kwargs)
        return page

    monkeypatch.setattr(project_browser_ui, "list_cloud_itinerary_page", fake_page)
    monkeypatch.setattr(project_browser_ui, "render_project_list", list_calls.append)
    monkeypatch.setattr(project_browser_ui, "render_selected_project_panel", detail_calls.append)

    project_browser_ui._render_cloud_project_browser()

    assert page_calls == [{"page_index": 0, "page_size": 12, "search": "", "sort": "recent"}]
    assert list_calls == [page]
    assert detail_calls == [page.projects[0]]
    assert st.session_state["open_project_selected_project_id"] == "project-1"


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
