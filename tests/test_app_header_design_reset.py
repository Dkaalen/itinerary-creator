from types import SimpleNamespace

from app_modules import app_header


def test_app_header_and_stage_panel_do_not_render_legacy_html(monkeypatch):
    calls = []
    fake_st = SimpleNamespace(
        html=lambda body: calls.append(("html", body)),
        markdown=lambda *args, **kwargs: calls.append(("markdown", args, kwargs)),
    )
    monkeypatch.setattr(app_header, "st", fake_st)

    assert app_header._stage_panel("Title", "Body") is None
    assert app_header._render_app_header("version", stage="input") is None
    assert app_header._render_top_nav("input") is None
    assert calls == []


def test_app_header_renders_compact_workspace_shell_for_active_itinerary(monkeypatch):
    calls = []
    fake_st = SimpleNamespace(
        session_state={
            "parsed_rows": [
                {"day": "Day 1", "type": "Hotel", "city": "Oslo"},
                {"day": "Day 2", "type": "Activity", "city": "Bergen"},
            ],
            "output_edits": {"trip_title": "Norway Winter", "pictures_added": True},
            "itinerary_name": "Norway Winter",
        },
        html=lambda body: calls.append(("html", body)),
        markdown=lambda *args, **kwargs: calls.append(("markdown", args, kwargs)),
    )
    monkeypatch.setattr(app_header, "st", fake_st)

    assert app_header._render_app_header("v-test", stage="pictures") is None

    assert len(calls) == 1
    assert calls[0][0] == "html"
    assert "workspace-shell" in calls[0][1]
    assert "Norway Winter" in calls[0][1]
    assert "2 days" in calls[0][1]
    assert "Add pictures" in calls[0][1]
    assert "Not saved" in calls[0][1]


def test_input_page_uses_compact_project_upload_and_calculator_entry(monkeypatch):
    from app_modules import calculator_navigation, project_browser_ui

    project_calls = []
    workspace_calls = []
    fake_project_st = SimpleNamespace(
        session_state={},
        button=lambda *args, **kwargs: project_calls.append((args, kwargs)) or True,
    )
    monkeypatch.setattr(project_browser_ui, "st", fake_project_st)
    monkeypatch.setattr(project_browser_ui, "_render_open_project_workspace", lambda: workspace_calls.append("opened"))

    project_browser_ui.render_open_project_file_action()

    assert project_calls == [(("Open project",), {"use_container_width": True, "help": "Open a saved cloud project or backup file."})]
    assert fake_project_st.session_state[project_browser_ui.OPEN_PROJECT_BROWSER_VISIBLE_KEY] is True
    assert workspace_calls == []

    project_browser_ui.render_open_project_workspace_if_visible()

    assert workspace_calls == ["opened"]

    nav_calls = []
    fake_nav_st = SimpleNamespace(
        session_state={},
        button=lambda *args, **kwargs: nav_calls.append(("button", args, kwargs)) or False,
        caption=lambda *args, **kwargs: nav_calls.append(("caption", args, kwargs)),
        rerun=lambda: nav_calls.append(("rerun", (), {})),
    )
    monkeypatch.setattr(calculator_navigation, "st", fake_nav_st)

    calculator_navigation.render_calculator_entry_button()

    assert nav_calls[0] == (
        "button",
        ("Open calculator",),
        {
            "use_container_width": True,
            "help": "Build, price, export, and generate an itinerary from the in-app spreadsheet.",
        },
    )
    assert nav_calls[1][0] == "caption"
    assert not any(call[0] == "rerun" for call in nav_calls)


def test_app_header_distinguishes_cloud_saved_from_cloud_dirty(monkeypatch):
    calls = []
    payload = {
        "metadata": {"project_id": "project-1", "itinerary_name": "Norway Winter"},
        "source": {"source_input": ""},
        "current_snapshot": {
            "parsed_rows": [{"day": "Day 1", "type": "Hotel", "city": "Oslo"}],
            "output_edits": {"trip_title": "Norway Winter"},
            "detail_level": "Rich descriptive",
            "day_page_layout": "Classic",
        },
    }
    session_state = {
        "parsed_rows": payload["current_snapshot"]["parsed_rows"],
        "output_edits": payload["current_snapshot"]["output_edits"],
        "itinerary_name": "Norway Winter",
        "detail_level": "Rich descriptive",
        "day_page_layout": "Classic",
        "raw_text_input": "",
        "active_project_cloud_persisted": True,
        "project_storage_last_saved_baseline": payload,
    }
    fake_st = SimpleNamespace(
        session_state=session_state,
        html=lambda body: calls.append(body),
    )
    monkeypatch.setattr(app_header, "st", fake_st)

    app_header._render_app_header("v-test", stage="edit")
    assert "Saved" in calls[-1]
    assert "Cloud saved" not in calls[-1]

    session_state["output_edits"] = {"trip_title": "Edited title"}
    app_header._render_app_header("v-test", stage="edit")
    assert "Unsaved changes" in calls[-1]
