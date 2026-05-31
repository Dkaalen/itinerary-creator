import json
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

