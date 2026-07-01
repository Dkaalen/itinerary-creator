from visual_editor_component.editor_payload_builder import build_visual_editor_payload
from tests.support.frontend_assets import frontend_script_names, frontend_source


def _frontend_script_names() -> tuple[str, ...]:
    return frontend_script_names()


def _frontend_source() -> str:
    return frontend_source()


def test_payload_carries_source_rows_and_generated_value_snapshot():
    rows = [
        {
            "row_id": "row-1",
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "date": "12 June 2027",
            "city": "Oslo",
            "title": "Guided walking tour",
            "details": "Meet the guide outside the hotel at 10:00.",
        }
    ]
    payload = build_visual_editor_payload(
        rows,
        {"Day 1": rows},
        {"pictures_added": False, "editor_draft": {"days": [{"day_id": "Day 1", "title": "Edited title"}]}},
    )

    assert payload["source_rows"]["row-1"]["title"] == "Guided walking tour"
    assert "Meet the guide" in payload["source_rows"]["row-1"]["source_text"]
    assert payload["days"][0]["title"] == "Edited title"
    assert payload["generated_values"]["days"][0]["title"] == "Guided walking tour"
    assert payload["generated_values"]["cover"]["route_label"] == "Route"
    assert payload["generated_values"]["final_pages"]["whats_included_title"] == "What’s included"




def test_compare_restore_split_modules_are_loaded_by_editor_assets():
    script_names = _frontend_script_names()

    assert "editor_assets.js" in script_names
    assert "editor_text_history.js" in script_names
    assert "editor_inspector_selection.js" in script_names
    assert script_names.index("editor_text_history.js") < script_names.index("editor_inspector_fields.js")
    assert script_names.index("editor_inspector_selection.js") < script_names.index("editor_inspector.js")


def test_frontend_exposes_compare_and_restore_to_generated_tools():
    source = _frontend_source()

    assert "generatedValueForKey" in source
    assert "restoreValueForKey" in source
    assert "fieldDiffState" in source
    assert "renderInspectorCompareTools" in source
    assert "Compare & restore" in source
    assert "inspectorRestoreCurrentGeneratedBtn" in source
    assert "inspectorRestoreSelectionGeneratedBtn" in source
    assert "resetSelectionFieldsToGenerated" in source


def test_frontend_source_panel_expands_linked_supplier_rows():
    source = _frontend_source()

    assert "sourceRowLookup" in source
    assert "renderSourceRowDetails" in source
    assert "source-row-detail" in source
    assert "source-row-meta" in source
    assert "No source text available in payload" in source
    assert "model?.source_rows" in source
