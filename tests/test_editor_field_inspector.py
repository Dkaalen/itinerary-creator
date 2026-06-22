from pathlib import Path


def _frontend_source() -> str:
    frontend = Path("visual_editor_component/frontend")
    return "\n".join(
        (frontend / relative).read_text(encoding="utf-8")
        for relative in (
            "styles/editor.css",
            "js/state.js",
            "js/render.js",
            "js/serialization.js",
            "js/commands.js",
            "js/editing.js",
        )
    )


def test_right_inspector_exposes_direct_field_editor():
    source = _frontend_source()

    assert "renderInspectorFieldEditor" in source
    assert "inspectorFieldEditor" in source
    assert "applyInspectorFieldEdit" in source
    assert "data-inspector-edit-key" in source
    assert "Field editor" in source
    assert "Apply field edit" in source


def test_right_inspector_lists_and_selects_editable_fields():
    source = _frontend_source()

    assert "inspectorFieldEntriesForSelection" in source
    assert "renderInspectorFieldList" in source
    assert "data-inspector-field-key" in source
    assert "selectInspectorField" in source
    assert "field-list" in source
    assert "inspector-field-row" in source


def test_field_reset_controls_are_available_per_selected_field():
    source = _frontend_source()

    assert "resetFieldByKey" in source
    assert "resetSelectedInspectorField" in source
    assert "data-inspector-reset-field-key" in source
    assert "inspectorResetSingleFieldBtn" in source
    assert "Reset field" in source


def test_field_inspector_covers_core_page_types():
    source = _frontend_source()

    assert "cover.trip_title" in source
    assert "summary.trip_glance" in source
    assert "summary.journey_arc" in source
    assert "`days.${index}.${name}`" in source
    assert "`final_pages.whats_included_pages_html.${index}.html`" in source
    assert "`document_pages.${pageIndex}.manual_blocks.${blockIndex}.editable_fields.content_html`" in source
