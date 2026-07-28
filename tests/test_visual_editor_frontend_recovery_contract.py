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

import visual_editor_component.editor_workflow as editor_workflow
from visual_editor_component.editor_workflow import apply_visual_editor_result
from tests.support.frontend_assets import frontend_source


def _visual_editor_frontend_source():
    return frontend_source()


def test_visual_editor_v2_contract_is_inline_not_separate_form():
    editor_html = _visual_editor_frontend_source()

    assert "Save changes" in editor_html
    assert "hover an image to edit it on the canvas" in editor_html
    assert "data-select-image-field" in editor_html
    assert "cover.trip_dates" in editor_html
    assert "Undo" in editor_html
    assert "Reset section" in editor_html
    assert "Replace all" in editor_html
    assert "Font" in editor_html
    assert "Size" in editor_html
    assert "Text color / highlight" in editor_html
    assert "Compact" in editor_html
    assert "Normal spacing" in editor_html
    assert "Flag issue" in editor_html
    assert "warning-hit" in editor_html
    assert "function flagSelectedIssue" in editor_html


def test_visual_editor_frontend_has_autosave_and_text_first_contract():
    editor_html = _visual_editor_frontend_source()

    assert "Edit itinerary text" in editor_html
    assert "Browser recovery saves while you work" in editor_html
    assert "window.indexedDB" in editor_html
    assert "writeVisualDraftRaw" in editor_html
    assert "localStorage.setItem" not in editor_html
    assert "beforeunload" in editor_html
    assert "visibilitychange" in editor_html
    assert "pagehide" in editor_html
    assert "picturesAdded" in editor_html
    assert "Applying changes…" in editor_html


def test_visual_editor_text_mode_cover_uses_high_contrast_edit_skin():
    editor_html = _visual_editor_frontend_source()

    assert "editor-text-cover" in editor_html
    assert "cover-page.editor-text-cover .cover-title" in editor_html
    assert "picturesAdded() ? '' : 'editor-text-cover'" in editor_html


def test_visual_editor_recovered_browser_draft_waits_for_explicit_save():
    editor_html = _visual_editor_frontend_source()

    assert "restoredLocalDraftPendingSave" in editor_html
    assert "saveRestoredLocalDraftToServer" in editor_html
    assert "Recovered browser draft. Use Save changes to sync it." in editor_html
    assert "Recovered browser draft synced" in editor_html
    assert "serverSnapshot === localSnapshot" in editor_html
    assert "setTimeout(saveRestoredLocalDraftToServer, 0)" not in editor_html


def test_visual_editor_frontend_rejects_stale_local_draft_signatures():
    editor_html = _visual_editor_frontend_source()

    assert "source_signature: initialPayload?.meta?.source_signature" in editor_html
    assert "currentSourceSignature" in editor_html
    assert "savedSourceSignature" in editor_html
    assert "currentSourceSignature !== savedSourceSignature" in editor_html


def test_visual_editor_frontend_keeps_server_picture_workflow_authoritative():
    editor_html = _visual_editor_frontend_source()

    assert "const serverPicturesAdded = !!initialPayload?.workflow?.pictures_added" in editor_html
    assert "if (serverPicturesAdded && localPicturesAdded && localDay.image)" in editor_html
    assert "if (serverPicturesAdded)" in editor_html
    assert "merged.workflow.pictures_added = !!localDraft.workflow.pictures_added" not in editor_html
    assert "workflowPromotedToPictures" in editor_html
    assert "if (incomingPicturesAdded) model.workflow.pictures_added = true" in editor_html


def test_visual_editor_frontend_merges_recovered_days_by_identity_not_only_index():
    editor_html = _visual_editor_frontend_source()

    assert "function sameDraftDay" in editor_html
    assert "function findServerDayForLocalDraft" in editor_html
    assert "sameDraftDay(day, localDay, fallbackIndex)" in editor_html


def test_visual_editor_commit_strips_clipboard_fragment_markers():
    output_edits = {"days": {}}
    result = json.dumps({
        "cover": {},
        "summary": {},
        "days": [
            {"day": "Day 3", "blocks_html": "<div>Included journey: StartFragmentBergen RailwayEndFragment</div>"},
        ],
        "final_pages": {
            "whats_included_pages_html": [{"html": "<div>StartFragmentFlight from Bergen to TromsøEndFragment</div>"}],
        },
    })

    assert apply_visual_editor_result(result, output_edits)

    assert "StartFragment" not in output_edits["days"]["Day 3"]["blocks_html"]
    assert "EndFragment" not in output_edits["whats_included_pages_html"][0]
    assert "Bergen Railway" in output_edits["days"]["Day 3"]["blocks_html"]


def test_render_document_reads_typed_day_titles_without_legacy_mirror():
    from app_modules.itinerary_render_context import build_itinerary_render_context

    rows = [
        {
            "row_id": "r1",
            "day": "Day 1",
            "date": "01/01/2027",
            "city": "Oslo",
            "type": "Arrival",
            "effective_type": "Arrival",
            "title": "Welcome to Oslo",
        }
    ]
    output_edits = {
        "editor_draft": {
            "schema_version": 3,
            "days": [
                {
                    "day_id": "Day 1",
                    "label": "Day 1",
                    "title": "Edited Preview Title",
                    "city": "Oslo",
                    "intro": "Edited preview intro.",
                    "blocks": [],
                }
            ],
        }
    }

    context = build_itinerary_render_context(rows, {"Day 1": rows}, output_edits)

    assert context.render_document.days[0].title == "Edited Preview Title"
    assert context.render_document.days[0].intro == "Edited preview intro."


def test_visual_editor_bridge_injects_storage_contract_without_mutating_payload(monkeypatch):
    import visual_editor_component.editor_bridge as bridge

    calls = []
    monkeypatch.setattr(bridge, "_visual_page_editor", lambda **kwargs: calls.append(kwargs) or "result")
    payload = {"draft_id": "visual-test"}

    assert bridge.render_visual_page_editor(payload, key="editor-key") == "result"
    assert "browser_storage_contract" not in payload
    assert calls[0]["payload"]["browser_storage_contract"]["owners"]["visual_editor"]["current_prefix"] == "itinerary-visual-editor-draft:"
