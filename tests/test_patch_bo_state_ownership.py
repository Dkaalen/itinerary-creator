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

import visual_editor_component.editor_result_applier as result_applier
from visual_editor_component.editor_workflow import apply_visual_editor_result


def test_visual_editor_rejects_payload_from_different_source_signature():
    result_applier.st.session_state = {"_visual_editor_current_source_signature": "source-new"}
    output_edits = {"days": {}, "trip_title": "Original title"}
    result = json.dumps(
        {
            "meta": {"source_signature": "source-old"},
            "cover": {"trip_title": "Stale title"},
            "summary": {},
            "days": [],
            "final_pages": {},
        }
    )

    assert apply_visual_editor_result(result, output_edits) is False

    assert output_edits["trip_title"] == "Original title"
    assert result_applier.st.session_state["_visual_editor_last_result_changed"] is False


def test_visual_editor_accepts_matching_source_signature():
    result_applier.st.session_state = {"_visual_editor_current_source_signature": "source-live"}
    output_edits = {"days": {}}
    result = json.dumps(
        {
            "meta": {"source_signature": "source-live"},
            "cover": {"trip_title": "Fresh title"},
            "summary": {},
            "days": [],
            "final_pages": {},
        }
    )

    assert apply_visual_editor_result(result, output_edits) is True

    assert output_edits["trip_title"] == "Fresh title"


def test_visual_editor_accepts_legacy_payload_without_source_signature():
    result_applier.st.session_state = {"_visual_editor_current_source_signature": "source-live"}
    output_edits = {"days": {}}
    result = json.dumps(
        {
            "cover": {"trip_title": "Legacy payload"},
            "summary": {},
            "days": [],
            "final_pages": {},
        }
    )

    assert apply_visual_editor_result(result, output_edits) is True

    assert output_edits["trip_title"] == "Legacy payload"
