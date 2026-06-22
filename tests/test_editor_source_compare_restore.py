from pathlib import Path

from visual_editor_component.editor_payload_builder import build_visual_editor_payload


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/state.js",
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
        )
    )


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
