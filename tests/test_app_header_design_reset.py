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
    assert "Oslo → Bergen" in calls[0][1]
    assert "Add pictures" in calls[0][1]
    assert "Next · review images" in calls[0][1]


def test_input_page_uses_compact_project_upload_and_calculator_entry():
    project_source = __import__("pathlib").Path("app_modules/project_file_ui.py").read_text()
    nav_source = __import__("pathlib").Path("app_modules/calculator_navigation.py").read_text()

    assert 'st.expander("Open saved project", expanded=False)' in project_source
    assert 'st.container(border=True)' not in project_source
    assert 'st.button("Open calculator", type="primary"' in nav_source
    assert '"Calculate itinerary", type="primary", use_container_width=True' not in nav_source
