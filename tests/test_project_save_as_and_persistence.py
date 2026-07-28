from __future__ import annotations

from datetime import datetime, timezone

from app_modules.project_persistence_state import (
    active_cloud_project_is_persisted,
    mark_cloud_project_persisted,
)
from app_modules.project_save_as import prepare_project_save_as_payload
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.project_storage_workflow import save_pdf_export


def test_save_as_payload_gets_fresh_identity_name_and_timestamps() -> None:
    source = {
        "metadata": {
            "project_id": "original-id",
            "itinerary_name": "Original",
            "created_at": "2026-07-01T10:00:00Z",
            "updated_at": "2026-07-02T10:00:00Z",
            "status": "active",
        },
        "current_snapshot": {"parsed_rows": [{"day": 1}]},
    }

    copied = prepare_project_save_as_payload(
        source,
        new_name="  Norway   Option B  ",
        id_factory=lambda: "new-id",
        clock=lambda: datetime(2026, 7, 27, 12, 30, tzinfo=timezone.utc),
    )

    assert copied["metadata"] == {
        "project_id": "new-id",
        "itinerary_name": "Norway Option B",
        "created_at": "2026-07-27T12:30:00Z",
        "updated_at": "2026-07-27T12:30:00Z",
        "status": "active",
    }
    assert copied["current_snapshot"] == source["current_snapshot"]
    assert source["metadata"]["project_id"] == "original-id"


def test_save_as_rejects_blank_and_overlong_names() -> None:
    for name in ("   ", "x" * 161):
        try:
            prepare_project_save_as_payload({}, new_name=name)
        except ValueError:
            pass
        else:  # pragma: no cover - assertion branch
            raise AssertionError("invalid project name was accepted")


def test_cloud_persistence_marker_keeps_saved_baseline_separate_from_live_project() -> None:
    baseline = {
        "metadata": {"project_id": "project-1", "itinerary_name": "Trip"},
        "source": {"source_input": "Day 1"},
        "current_snapshot": {
            "parsed_rows": [{"day": 1, "title": "Saved"}],
            "output_edits": {"trip_title": "Saved"},
            "detail_level": "Rich descriptive",
            "day_page_layout": "Classic",
        },
    }
    state = {
        "active_saved_project": {
            **baseline,
            "current_snapshot": {
                **baseline["current_snapshot"],
                "output_edits": {"trip_title": "Live edit"},
            },
        },
        "itinerary_name": "Trip",
        "parsed_rows": [{"day": 1, "title": "Saved"}],
        "output_edits": {"trip_title": "Live edit"},
        "detail_level": "Rich descriptive",
        "day_page_layout": "Classic",
        "raw_text_input": "Day 1",
    }
    mark_cloud_project_persisted(state, payload=baseline, version_id="version-1")

    assert active_cloud_project_is_persisted(state) is True
    assert active_project_has_unsaved_changes(state) is True


def test_pdf_export_does_not_create_or_write_an_unsaved_cloud_project(monkeypatch) -> None:
    class Repository:
        def __getattr__(self, name):  # pragma: no cover - only called on regression
            raise AssertionError(f"unexpected repository call: {name}")

    monkeypatch.setattr(
        "app_modules.project_storage_workflow.get_project_storage_repository",
        lambda: Repository(),
    )

    assert save_pdf_export(
        {"active_project_storage_id": "local-only-id", "output_edits": {"output_brand": "agent"}},
        content=b"pdf",
        filename="trip.pdf",
    ) is False


def test_save_as_workflow_switches_to_new_project_only_after_remote_success(monkeypatch) -> None:
    from app_modules import project_storage_workflow as workflow

    class Repository:
        def __init__(self) -> None:
            self.upserts = []
            self.versions = []

        def next_version_number(self, itinerary_id, itinerary_type):
            assert itinerary_id == "new-id"
            return 1

        def upsert_itinerary(self, itinerary_id, *, name, status="draft"):
            self.upserts.append((itinerary_id, name, status))
            return {"id": itinerary_id}

        def create_itinerary(self, itinerary_id, *, name, status="draft"):
            self.upserts.append((itinerary_id, name, status))
            return {"id": itinerary_id}

        def create_version(self, **payload):
            self.versions.append(payload)
            return {"id": "new-version-id"}

        def delete_itinerary(self, itinerary_id):  # pragma: no cover - rollback only
            raise AssertionError(f"unexpected rollback for {itinerary_id}")

    repository = Repository()
    monkeypatch.setattr(workflow, "get_project_storage_repository", lambda: repository)
    state = {
        "active_project_storage_id": "old-id",
        "active_saved_project_id": "old-id",
        "active_project_cloud_persisted": True,
        "itinerary_name": "Old trip",
        "project_storage_last_calculator_file_path": "itineraries/old-id/calculator/old.xlsx",
        "project_storage_last_calculator_snapshot": {"rows": [{"id": "old"}]},
        "project_storage_last_pdf_path": "itineraries/old-id/exports/agent/old.pdf",
        "cloud_calculator_file_payload_old": b"old",
    }
    payload = {
        "metadata": {"project_id": "new-id", "itinerary_name": "New option", "status": "active"},
        "output_brand": "agent",
        "mode": "agent",
    }

    assert workflow.save_project_payload_snapshot(
        state,
        payload,
        source_type="save_as",
        project_id_override="new-id",
        project_was_persisted=False,
    ) is True

    assert repository.upserts == [("new-id", "New option", "active")]
    assert repository.versions[0]["itinerary_id"] == "new-id"
    assert repository.versions[0]["version_number"] == 1
    assert state["active_project_storage_id"] == "new-id"
    assert state["active_saved_project_id"] == "new-id"
    assert state["itinerary_name"] == "New option"
    assert state["project_storage_last_saved_version_id"] == "new-version-id"
    assert "project_storage_last_calculator_file_path" not in state
    assert "project_storage_last_calculator_snapshot" not in state
    assert "project_storage_last_pdf_path" not in state
    assert "cloud_calculator_file_payload_old" not in state


def test_generation_module_has_no_implicit_cloud_save_trigger() -> None:
    from tests.support.static_contracts import read_contract_text

    source = read_contract_text("app_modules/generation_action.py")

    assert "save_generated_project_snapshot" not in source


def test_save_as_form_uses_new_identity_without_overwriting_current_project(monkeypatch) -> None:
    from types import SimpleNamespace
    from tests.support.streamlit_stub import SessionState, install_streamlit_stub
    from app_modules import project_save_ui

    st = install_streamlit_stub(force=True)
    state = SessionState(
        {
            "project_save_as_visible": True,
            "save_as_cloud_project_name_test": "Stale copy name",
            "itinerary_name": "Original",
            "active_project_storage_id": "old-id",
            "active_saved_project_id": "old-id",
            "active_project_cloud_persisted": True,
        }
    )
    st.session_state = state
    project_save_ui.st.session_state = state
    saved_calls = []
    success_messages = []

    monkeypatch.setattr(project_save_ui.st, "text_input", lambda *args, **kwargs: "New option")
    monkeypatch.setattr(
        project_save_ui.st,
        "form_submit_button",
        lambda label, **kwargs: label == "Save as copy",
    )
    monkeypatch.setattr(
        project_save_ui,
        "prepare_saved_project_file_download",
        lambda session: SimpleNamespace(payload={"metadata": {"project_id": "old-id", "itinerary_name": "Original"}}),
    )
    monkeypatch.setattr(
        project_save_ui,
        "prepare_project_save_as_payload",
        lambda payload, *, new_name: {"metadata": {"project_id": "new-id", "itinerary_name": new_name}},
    )

    def save(session, payload, **kwargs):
        saved_calls.append((payload, kwargs))
        session["active_project_storage_id"] = kwargs["project_id_override"]
        session["active_saved_project_id"] = kwargs["project_id_override"]
        return True

    monkeypatch.setattr(project_save_ui, "save_project_payload_snapshot", save)
    monkeypatch.setattr(project_save_ui.st, "success", lambda message: success_messages.append(str(message)))
    monkeypatch.setattr(project_save_ui.st, "toast", lambda message, **kwargs: success_messages.append(str(message)))

    project_save_ui._render_save_as_form(key_suffix="test")

    assert saved_calls == [
        (
            {"metadata": {"project_id": "new-id", "itinerary_name": "New option"}},
            {
                "source_type": "save_as",
                "project_id_override": "new-id",
                "project_was_persisted": False,
            },
        )
    ]
    assert state["active_project_storage_id"] == "new-id"
    assert "project_save_as_visible" not in state
    assert "save_as_cloud_project_name_test" not in state
    assert success_messages == ["Copy saved"]


def test_current_save_rejects_blank_project_name_before_remote_write(monkeypatch) -> None:
    from tests.support.streamlit_stub import SessionState, install_streamlit_stub
    from app_modules import project_save_ui

    st = install_streamlit_stub(force=True)
    state = SessionState(
        {
            "itinerary_name": "   ",
            "itinerary_name_input": "   ",
            "active_project_storage_id": "project-1",
            "active_saved_project_id": "project-1",
            "active_project_cloud_persisted": True,
        }
    )
    st.session_state = state
    project_save_ui.st.session_state = state
    warnings = []

    monkeypatch.setattr(
        project_save_ui,
        "prepare_saved_project_file_download",
        lambda session: (_ for _ in ()).throw(AssertionError("payload preparation must not run")),
    )
    monkeypatch.setattr(
        project_save_ui,
        "save_project_payload_snapshot",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote save must not run")),
    )
    monkeypatch.setattr(project_save_ui.st, "warning", lambda message: warnings.append(str(message)))

    project_save_ui._save_current_cloud_project()

    assert warnings == ["Enter a project name before saving."]
    assert state["itinerary_name"] == "   "
    assert state["itinerary_name_input"] == "   "


def test_current_save_normalizes_and_persists_edited_project_name(monkeypatch) -> None:
    from types import SimpleNamespace
    from tests.support.streamlit_stub import SessionState, install_streamlit_stub
    from app_modules import project_save_ui

    st = install_streamlit_stub(force=True)
    state = SessionState(
        {
            "itinerary_name": "Old name",
            "itinerary_name_input": "  Norway   Winter  ",
            "active_project_storage_id": "project-1",
            "active_saved_project_id": "project-1",
            "active_project_cloud_persisted": True,
        }
    )
    st.session_state = state
    project_save_ui.st.session_state = state
    saved_payloads = []

    def prepare(session):
        assert session["itinerary_name"] == "Norway Winter"
        assert session["itinerary_name_input"] == "Norway Winter"
        return SimpleNamespace(
            payload={
                "metadata": {
                    "project_id": "project-1",
                    "itinerary_name": session["itinerary_name"],
                }
            }
        )

    monkeypatch.setattr(project_save_ui, "prepare_saved_project_file_download", prepare)

    def save(session, payload, **kwargs):
        saved_payloads.append((payload, kwargs))
        return True

    monkeypatch.setattr(project_save_ui, "save_project_payload_snapshot", save)
    monkeypatch.setattr(project_save_ui.st, "success", lambda message: None)

    project_save_ui._save_current_cloud_project()

    assert saved_payloads == [
        (
            {
                "metadata": {
                    "project_id": "project-1",
                    "itinerary_name": "Norway Winter",
                }
            },
            {"source_type": "manual_save"},
        )
    ]
