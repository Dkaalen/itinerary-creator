from app_modules.project_save_rollback import capture_project_save_baseline, restore_project_save_baseline


def test_failed_cloud_save_restores_previous_project_baseline() -> None:
    state = {
        "active_saved_project": {"metadata": {"project_id": "old"}},
        "active_project_storage_id": "old",
        "active_saved_project_id": "old",
        "itinerary_name": "Old name",
        "itinerary_name_input": "Old name",
        "active_project_cloud_persisted": True,
        "project_storage_last_saved_version_id": "version-old",
        "project_storage_last_saved_baseline": {"metadata": {"project_id": "old"}},
        "calculator_state": "latest calculator remains untouched",
    }
    baseline = capture_project_save_baseline(state)
    state.update(
        {
            "active_saved_project": {"metadata": {"project_id": "new"}},
            "active_project_storage_id": "new",
            "active_saved_project_id": "new",
            "itinerary_name": "New name",
            "itinerary_name_input": "New name",
            "active_project_cloud_persisted": False,
            "project_storage_last_saved_version_id": "version-new",
            "project_storage_last_saved_baseline": {"metadata": {"project_id": "new"}},
        }
    )

    restore_project_save_baseline(state, baseline)

    assert state["active_saved_project"]["metadata"]["project_id"] == "old"
    assert state["active_project_storage_id"] == "old"
    assert state["active_saved_project_id"] == "old"
    assert state["itinerary_name"] == "Old name"
    assert state["itinerary_name_input"] == "Old name"
    assert state["active_project_cloud_persisted"] is True
    assert state["project_storage_last_saved_version_id"] == "version-old"
    assert state["project_storage_last_saved_baseline"]["metadata"]["project_id"] == "old"
    assert state["calculator_state"] == "latest calculator remains untouched"


def test_cloud_save_failure_restores_baseline_without_losing_live_calculator(monkeypatch) -> None:
    import sys
    from types import ModuleType, SimpleNamespace

    diagnostics_stub = ModuleType("diagnostics")
    diagnostics_stub.warn_exception = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "diagnostics", diagnostics_stub)

    from tests.support.streamlit_stub import SessionState, install_streamlit_stub

    st = install_streamlit_stub(force=True)
    import app_modules.project_save_ui as project_save_ui

    live_calculator = object()
    state = SessionState(
        {
            "active_saved_project": {"metadata": {"project_id": "old", "itinerary_name": "Old"}},
            "active_project_storage_id": "old",
            "active_saved_project_id": "old",
            "itinerary_name": "Old",
            "calculator_state": live_calculator,
        }
    )
    st.session_state = state
    project_save_ui.st.session_state = state
    warnings: list[str] = []

    monkeypatch.setattr(project_save_ui.st, "button", lambda *args, **kwargs: True)
    monkeypatch.setattr(project_save_ui.st, "warning", lambda message: warnings.append(str(message)))

    def prepare(mutating_state):
        mutating_state["active_saved_project"] = {"metadata": {"project_id": "new", "itinerary_name": "New"}}
        mutating_state["active_project_storage_id"] = "new"
        mutating_state["active_saved_project_id"] = "new"
        mutating_state["itinerary_name"] = "New"
        return SimpleNamespace(payload={"metadata": {"project_id": "new"}})

    def fail_save(mutating_state, payload, *, source_type):
        mutating_state["project_storage_last_error"] = "Cloud write failed."
        return False

    monkeypatch.setattr(project_save_ui, "prepare_saved_project_file_download", prepare)
    monkeypatch.setattr(project_save_ui, "save_project_payload_snapshot", fail_save)

    project_save_ui._render_cloud_save_project_action(key_suffix="test")

    assert state["active_saved_project"]["metadata"]["project_id"] == "old"
    assert state["active_project_storage_id"] == "old"
    assert state["active_saved_project_id"] == "old"
    assert state["itinerary_name"] == "Old"
    assert state["calculator_state"] is live_calculator
    assert warnings == ["Cloud write failed."]
