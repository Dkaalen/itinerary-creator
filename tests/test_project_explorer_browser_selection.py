from __future__ import annotations

from tests.support.project_explorer_browser_harness import (
    component_values,
    open_project_explorer_browser_page,
    project_explorer_payload,
)


def test_rapid_checkbox_selection_stays_in_browser_until_explicit_review() -> None:
    manager, browser, page, _payload = open_project_explorer_browser_page()
    try:
        page.locator('[data-project-select="project-1"]').check()
        page.locator('[data-project-select="project-2"]').check()
        page.locator('[data-project-select="project-3"]').check()

        assert component_values(page) == []
        assert page.locator("[data-selection-count]").inner_text() == "3 projects selected"

        page.locator('[data-action="commit"]').click()
        values = component_values(page)
        assert len(values) == 1
        assert values[0]["action"] == "commit_selection"
        assert values[0]["selected_project_ids"] == ["project-1", "project-2", "project-3"]
        assert [project["id"] for project in values[0]["selected_projects"]] == [
            "project-1",
            "project-2",
            "project-3",
        ]
    finally:
        browser.close()
        manager.stop()


def test_sort_rerender_preserves_exact_ids_without_transferring_row_selection() -> None:
    manager, browser, page, payload = open_project_explorer_browser_page()
    try:
        page.locator('[data-project-select="project-2"]').check()
        sorted_payload = dict(payload)
        sorted_payload["rows"] = list(reversed(payload["rows"]))
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', "
            "{data: {type: 'streamlit:render', args: {payload}}}))",
            sorted_payload,
        )

        assert page.locator('[data-project-select="project-2"]').is_checked() is True
        assert page.locator('[data-project-select="project-1"]').is_checked() is False
        assert page.locator('[data-project-select="project-3"]').is_checked() is False
        assert component_values(page) == []
    finally:
        browser.close()
        manager.stop()


def test_page_action_submits_selection_once_with_durable_ids() -> None:
    manager, browser, page, _payload = open_project_explorer_browser_page()
    try:
        page.locator('[data-project-select="project-1"]').check()
        page.locator('[data-project-select="project-3"]').check()
        page.locator('[data-action="next"]').click()

        values = component_values(page)
        assert len(values) == 1
        assert values[0]["action"] == "page"
        assert values[0]["page_delta"] == 1
        assert values[0]["selected_project_ids"] == ["project-1", "project-3"]
    finally:
        browser.close()
        manager.stop()


def test_list_revision_change_resets_browser_selection_to_server_authority() -> None:
    manager, browser, page, payload = open_project_explorer_browser_page()
    try:
        page.locator('[data-project-select="project-1"]').check()
        changed = project_explorer_payload(revision=1, selected_ids=["project-3"])
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', "
            "{data: {type: 'streamlit:render', args: {payload}}}))",
            changed,
        )

        assert page.locator('[data-project-select="project-1"]').is_checked() is False
        assert page.locator('[data-project-select="project-3"]').is_checked() is True
        assert page.locator("[data-selection-count]").inner_text() == "1 project selected"
    finally:
        browser.close()
        manager.stop()


def test_new_streamlit_session_cannot_restore_previous_tab_selection() -> None:
    manager, browser, page, payload = open_project_explorer_browser_page()
    try:
        page.locator('[data-project-select="project-1"]').check()
        new_session = dict(payload)
        new_session["selection_session_id"] = "new-streamlit-session"
        new_session["selected_project_ids"] = ["project-3"]
        new_session["selected_projects"] = [payload["rows"][2]]
        page.evaluate(
            "payload => window.dispatchEvent(new MessageEvent('message', "
            "{data: {type: 'streamlit:render', args: {payload}}}))",
            new_session,
        )

        assert page.locator('[data-project-select="project-1"]').is_checked() is False
        assert page.locator('[data-project-select="project-3"]').is_checked() is True
    finally:
        browser.close()
        manager.stop()


def test_clear_selection_is_explicit_and_submits_no_project_ids() -> None:
    manager, browser, page, _payload = open_project_explorer_browser_page(
        project_explorer_payload(selected_ids=["project-1", "project-2"])
    )
    try:
        page.locator('[data-action="clear"]').click()

        values = component_values(page)
        assert len(values) == 1
        assert values[0]["action"] == "clear_selection"
        assert values[0]["selected_project_ids"] == []
    finally:
        browser.close()
        manager.stop()


def test_project_explorer_computed_button_states_use_readable_booknordics_colors() -> None:
    manager, browser, page, _payload = open_project_explorer_browser_page()
    try:
        disabled = page.locator('[data-action="commit"]').evaluate(
            "element => ({color: getComputedStyle(element).color, background: getComputedStyle(element).backgroundColor, opacity: getComputedStyle(element).opacity})"
        )
        assert disabled == {
            "color": "rgb(101, 98, 92)",
            "background": "rgb(231, 228, 221)",
            "opacity": "1",
        }

        page.locator('[data-project-select="project-1"]').check()
        enabled = page.locator('[data-action="commit"]').evaluate(
            "element => ({color: getComputedStyle(element).color, background: getComputedStyle(element).backgroundColor})"
        )
        assert enabled == {"color": "rgb(255, 255, 255)", "background": "rgb(35, 52, 70)"}
    finally:
        browser.close()
        manager.stop()
