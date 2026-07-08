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
