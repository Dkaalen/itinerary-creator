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


def _visual_editor_frontend_source():
    frontend = Path("visual_editor_component/frontend")
    parts = [(frontend / "index.html").read_text(encoding="utf-8")]
    for relative in (
        "styles/editor.css",
        "js/state.js",
        "js/images.js",
        "js/render.js",
        "js/serialization.js",
        "js/editor_dirty_state.js",
            "js/editor_text_tools.js",
            "js/editor_document_model.js",
            "js/editor_inspector.js",
            "js/editor_page_actions.js",
            "js/editor_warnings.js",
            "js/commands.js",
        "js/editing.js",
        "js/streamlit_bridge.js",
    ):
        parts.append((frontend / relative).read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_visual_editor_minimal_save_does_not_freeze_generated_inclusions():
    output_edits = {"days": {}}
    result = json.dumps({
        "cover": {"trip_title": "Edited trip"},
        "summary": {},
        "days": [],
        "final_pages": {},
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["trip_title"] == "Edited trip"
    assert "whats_included_html" not in output_edits


def test_visual_editor_keeps_inclusion_html_only_when_explicitly_edited():
    output_edits = {"days": {}}
    result = json.dumps({
        "cover": {},
        "summary": {},
        "days": [],
        "final_pages": {"whats_included_html": "<div>Edited inclusions</div>"},
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["whats_included_html"] == "<div>Edited inclusions</div>"


def test_visual_editor_normalizes_route_line_breaks_from_editable_preview():
    output_edits = {"days": {}}
    result = json.dumps({
        "cover": {"destinations_line": "Helsinki · Rovaniemi\nBergen · Oslo"},
        "summary": {},
        "days": [],
        "final_pages": {},
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["destinations_line"] == "Helsinki · Rovaniemi · Bergen · Oslo"


def test_visual_editor_accepts_pdf_export_commit_envelope():
    editor_workflow.st.session_state = {}
    output_edits = {"days": {}}
    result = json.dumps({
        "commit_nonce": "7",
        "payload": {
            "cover": {"trip_title": "Edited before PDF"},
            "summary": {},
            "days": [],
            "final_pages": {},
        },
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["trip_title"] == "Edited before PDF"
    assert editor_workflow.st.session_state["_visual_editor_last_applied_commit_nonce"] == "7"


def test_stale_visual_editor_payload_cannot_disable_added_pictures():
    editor_workflow.st.session_state = {}
    output_edits = {"days": {}, "pictures_added": True}
    result = json.dumps({
        "workflow": {"pictures_added": False},
        "cover": {},
        "summary": {},
        "days": [],
        "final_pages": {},
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["pictures_added"] is True


def test_visual_editor_can_promote_picture_state_from_recovered_payload():
    editor_workflow.st.session_state = {}
    output_edits = {"days": {}, "pictures_added": False}
    result = json.dumps({
        "workflow": {"pictures_added": True},
        "cover": {},
        "summary": {},
        "days": [],
        "final_pages": {},
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["pictures_added"] is True


def test_pdf_export_commit_applies_route_and_day_title_edits():
    editor_workflow.st.session_state = {}
    output_edits = {"days": {}}
    result = json.dumps({
        "commit_nonce": "12",
        "payload": {
            "cover": {
                "destinations_line": "Helsinki · Rovaniemi\nBergen · Oslo",
            },
            "summary": {},
            "days": [
                {"day": "Day 2", "title": "Edited Tallinn Adventure"},
            ],
            "final_pages": {},
        },
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["destinations_line"] == "Helsinki · Rovaniemi · Bergen · Oslo"
    assert output_edits["days"]["Day 2"]["title"] == "Edited Tallinn Adventure"
    assert editor_workflow.st.session_state["_visual_editor_last_applied_commit_nonce"] == "12"



def test_visual_editor_applies_cover_date_edits_from_inline_preview():
    output_edits = {"days": {}}
    result = json.dumps({
        "cover": {"trip_dates": "10th of January - 16th of January"},
        "summary": {},
        "days": [],
        "final_pages": {},
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["trip_dates"] == "10th of January - 16th of January"


def test_visual_editor_persists_flagged_issue_notes_for_future_patches():
    output_edits = {"days": {}}
    result = json.dumps({
        "cover": {},
        "summary": {},
        "days": [],
        "final_pages": {},
        "issue_flags": [
            {
                "key": "days.0.blocks_html",
                "label": "Day 1",
                "original": "self Transfer from A to B, Pls request at reception",
                "corrected": "Self-arranged transfer from A to B.",
            }
        ],
    })

    assert apply_visual_editor_result(result, output_edits)

    assert output_edits["visual_editor_issue_flags"] == [
        {
            "key": "days.0.blocks_html",
            "label": "Day 1",
            "original": "self Transfer from A to B, Pls request at reception",
            "corrected": "Self-arranged transfer from A to B.",
        }
    ]


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


def test_visual_editor_persists_intentionally_empty_day_blocks():
    output_edits = {"days": {}}
    result = json.dumps({
        "cover": {},
        "summary": {},
        "days": [
            {"day": "Day 1", "blocks_html": ""},
        ],
        "final_pages": {},
    })

    assert apply_visual_editor_result(result, output_edits)

    assert "blocks_html" in output_edits["days"]["Day 1"]
    assert output_edits["days"]["Day 1"]["blocks_html"] == ""


def test_visual_editor_payload_keeps_empty_saved_day_blocks_empty():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Rovaniemi",
            "title": "Generated Snowmobile Safari",
            "client_description": "Generated activity details",
            "time": "10:00 AM",
        }
    ]

    payload = editor_workflow.build_visual_editor_payload(
        rows,
        {"Day 1": rows},
        {"days": {"Day 1": {"blocks_html": ""}}, "important_travel_notes_text": ""},
    )

    assert payload["days"][0]["blocks_html"] == ""


def test_new_edit_state_starts_in_text_only_picture_workflow():
    from ui.output_edits import make_output_edit_state
    from ui.picture_workflow import pictures_are_added

    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Rovaniemi",
            "title": "Snowmobile Safari",
        }
    ]

    edits = make_output_edit_state(rows, {"Day 1": rows})

    assert edits["pictures_added"] is False
    assert pictures_are_added(edits) is False
    assert edits["draft_id"]


def test_visual_editor_payload_is_text_only_before_add_pictures():
    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Rovaniemi",
            "title": "Generated Snowmobile Safari",
            "client_description": "Generated activity details",
            "time": "10:00 AM",
        }
    ]

    payload = editor_workflow.build_visual_editor_payload(
        rows,
        {"Day 1": rows},
        {"days": {}, "important_travel_notes_text": "", "pictures_added": False, "draft_id": "draft-1"},
    )

    assert payload["workflow"] == {"pictures_added": False}
    assert payload["draft_id"] == "draft-1"
    assert payload["cover"]["cover_background_data_uri"] == ""
    assert payload["days"][0]["image"]["pictures_pending"] is True
    assert payload["days"][0]["image"]["data_uri"] == ""
    assert payload["days"][0]["image"]["options"] == []


def test_preview_html_omits_day_images_until_pictures_are_added():
    from app_modules.itinerary_html import build_itinerary_html

    rows = [
        {
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Rovaniemi",
            "title": "Snowmobile Safari",
            "client_description": "Generated activity details",
            "time": "10:00 AM",
        }
    ]

    html = build_itinerary_html(
        rows,
        {"Day 1": rows},
        {"days": {}, "important_travel_notes_text": "", "pictures_added": False},
    )

    assert '<div class="day-image-slot"' not in html
    assert "data:image/" not in html


def test_visual_editor_frontend_has_autosave_and_text_first_contract():
    editor_html = _visual_editor_frontend_source()

    assert "Edit itinerary text" in editor_html
    assert "Autosaving" in editor_html
    assert "localStorage.setItem" in editor_html
    assert "beforeunload" in editor_html
    assert "picturesAdded" in editor_html
    assert "Applying changes…" in editor_html


def test_visual_editor_text_mode_cover_uses_high_contrast_edit_skin():
    editor_html = _visual_editor_frontend_source()

    assert "editor-text-cover" in editor_html
    assert "cover-page.editor-text-cover .cover-title" in editor_html
    assert "picturesAdded() ? '' : 'editor-text-cover'" in editor_html

def test_visual_editor_recovered_browser_draft_is_saved_back_to_streamlit():
    editor_html = _visual_editor_frontend_source()

    assert "restoredLocalDraftPendingSave" in editor_html
    assert "saveRestoredLocalDraftToServer" in editor_html
    assert "Recovered browser draft and saved it" in editor_html
    assert "serverSnapshot === localSnapshot" in editor_html
    assert "setTimeout(saveRestoredLocalDraftToServer, 0)" in editor_html


def test_visual_editor_payload_includes_source_signature_for_draft_recovery():
    rows = [
        {
            "row_id": "row-1",
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Tromsø",
            "title": "Photo Tour to Arctic Landscapes and Fjords",
            "raw_text": "Supplier fjord photo tour details",
        }
    ]

    payload = editor_workflow.build_visual_editor_payload(
        rows,
        {"Day 1": rows},
        {"days": {}, "important_travel_notes_text": "", "pictures_added": False, "draft_id": "draft-1"},
    )

    assert payload["meta"]["draft_schema_version"] == 3
    assert payload["meta"]["day_count"] == 1
    assert payload["meta"]["source_signature"]

    changed_rows = [dict(rows[0], title="Munch Museum Admission")]
    changed_payload = editor_workflow.build_visual_editor_payload(
        changed_rows,
        {"Day 1": changed_rows},
        {"days": {}, "important_travel_notes_text": "", "pictures_added": False, "draft_id": "draft-1"},
    )

    assert changed_payload["meta"]["source_signature"] != payload["meta"]["source_signature"]


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
