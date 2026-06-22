import json
from pathlib import Path
import sys
import types

streamlit_stub = types.SimpleNamespace(
    warning=lambda *args, **kwargs: None,
    success=lambda *args, **kwargs: None,
    session_state={},
    components=types.SimpleNamespace(
        v1=types.SimpleNamespace(declare_component=lambda *args, **kwargs: (lambda **component_kwargs: None))
    ),
)
sys.modules.setdefault("streamlit", streamlit_stub)
sys.modules.setdefault("streamlit.components", streamlit_stub.components)
sys.modules.setdefault("streamlit.components.v1", streamlit_stub.components.v1)

from itinerary_generation.draft_autosave import (
    delete_autosave,
    draft_path,
    load_autosave_payload,
    save_autosave_payload,
)
import visual_editor_component.editor_workflow as editor_workflow
from visual_editor_component.editor_workflow import apply_visual_editor_result


def _frontend_source():
    frontend = Path("visual_editor_component/frontend")
    files = [
        "js/state.js",
        "js/serialization.js",
        "js/commands.js",
        "js/editing.js",
        "js/render.js",
    ]
    return "\n".join((frontend / name).read_text(encoding="utf-8") for name in files)


def test_autosave_payload_is_persisted_and_loaded(tmp_path):
    payload = {
        "draft_id": "draft/unsafe id",
        "meta": {"source_signature": "sig-1"},
        "cover": {"trip_title": "Edited trip"},
        "days": [{"day": "Day 1", "title": "Edited day"}],
        "final_pages": {},
    }

    result = save_autosave_payload(payload, base_dir=tmp_path)

    assert result["ok"] is True
    assert Path(result["path"]).exists()
    assert "draft-unsafe-id" in Path(result["path"]).name
    assert load_autosave_payload("draft/unsafe id", source_signature="sig-1", base_dir=tmp_path)["cover"]["trip_title"] == "Edited trip"
    assert load_autosave_payload("draft/unsafe id", source_signature="other", base_dir=tmp_path) is None
    assert delete_autosave("draft/unsafe id", base_dir=tmp_path) is True
    assert not draft_path("draft/unsafe id", base_dir=tmp_path).exists()


def test_visual_editor_autosave_envelope_saves_without_visible_manual_success(tmp_path, monkeypatch):
    editor_workflow.st.session_state = {}
    monkeypatch.setenv("ITINERARY_DRAFT_AUTOSAVE_DIR", str(tmp_path))
    output_edits = {"draft_id": "draft-test", "days": {}}
    result = json.dumps({
        "autosave": True,
        "payload": {
            "draft_id": "draft-test",
            "meta": {"source_signature": "sig-2"},
            "cover": {"trip_title": "Autosaved title"},
            "summary": {},
            "days": [],
            "final_pages": {},
        },
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["trip_title"] == "Autosaved title"
    assert editor_workflow.st.session_state["persistent_draft_status"]["ok"] is True
    assert editor_workflow.st.session_state["_visual_editor_last_result_was_autosave"] is True
    assert load_autosave_payload("draft-test", source_signature="sig-2", base_dir=tmp_path)["cover"]["trip_title"] == "Autosaved title"


def test_server_autosave_recovery_applies_matching_payload(tmp_path, monkeypatch):
    editor_workflow.st.session_state = {}
    monkeypatch.setenv("ITINERARY_DRAFT_AUTOSAVE_DIR", str(tmp_path))
    payload = {
        "draft_id": "recover-me",
        "meta": {"source_signature": "sig-3"},
        "cover": {"trip_title": "Recovered title"},
        "summary": {},
        "days": [{"day": "Day 1", "title": "Recovered Day"}],
        "final_pages": {},
    }
    save_autosave_payload(payload, base_dir=tmp_path)
    output_edits = {"draft_id": "recover-me", "days": {}}

    changed = editor_workflow._try_apply_server_autosave(
        {"draft_id": "recover-me", "meta": {"source_signature": "sig-3"}},
        output_edits,
    )

    assert changed is True
    assert output_edits["trip_title"] == "Recovered title"
    assert output_edits["days"]["Day 1"]["title"] == "Recovered Day"
    assert editor_workflow.st.session_state["persistent_draft_status"]["recovered"] is True


def test_frontend_contains_quiet_server_autosave_contract():
    source = _frontend_source()

    assert "SERVER_AUTOSAVE_DELAY_MS" in source
    assert "buildServerAutosaveEnvelope" in source
    assert "autosave: true" in source
    assert "sendServerAutosaveNow" in source
    assert "Changes autosave quietly while you work" in source
    assert "Autosaving…" in source


def test_server_autosave_uses_delta_payload_not_full_commit_model():
    source = _frontend_source()
    start = source.index("function buildServerAutosaveEnvelope")
    body = source[start:source.index("}", start) + 1]

    assert "const payload = pruneForSave(model);" in body
    assert "compactFullPayloadForCommit(model)" not in body
    assert "save_mode = 'delta'" in source
    assert "delta: true" in source


def test_autosaved_delta_payload_merges_with_existing_editor_state(tmp_path, monkeypatch):
    editor_workflow.st.session_state = {}
    monkeypatch.setenv("ITINERARY_DRAFT_AUTOSAVE_DIR", str(tmp_path))
    output_edits = {
        "draft_id": "delta-draft",
        "days": {"Day 1": {"title": "Old title", "blocks_html": "<div>Old block</div>"}},
        "editor_draft": {
            "schema_version": 3,
            "days": [
                {
                    "day_id": "Day 1",
                    "title": "Old title",
                    "blocks": [{"block_id": "main", "kind": "day_content", "content_html": "<div>Old block</div>"}],
                }
            ],
            "final_sections": [],
            "document_pages": [],
            "workflow": {},
            "issue_flags": [],
        },
    }
    result = json.dumps({
        "autosave": True,
        "delta": True,
        "payload": {
            "draft_id": "delta-draft",
            "meta": {"source_signature": "sig-delta"},
            "save_mode": "delta",
            "days": [{"day": "Day 1", "title": "New title"}],
            "editor_draft": {
                "schema_version": 3,
                "days": [{"day_id": "Day 1", "title": "New title"}],
                "final_sections": [],
                "document_pages": [],
                "workflow": {},
                "issue_flags": [],
            },
        },
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["days"]["Day 1"]["title"] == "New title"
    assert output_edits["days"]["Day 1"]["blocks_html"] == "<div>Old block</div>"
    saved = load_autosave_payload("delta-draft", source_signature="sig-delta", base_dir=tmp_path)
    assert saved["save_mode"] == "delta"
