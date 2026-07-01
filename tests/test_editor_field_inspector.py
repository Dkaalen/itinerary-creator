from pathlib import Path
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_right_inspector_does_not_render_text_content_editor_by_default():
    source = _frontend_source()
    render_right = source[source.index("function renderRightInspector"):]

    assert "renderInspectorFieldEditor" in source
    assert "inspectorFieldEditor" in source
    assert "applyInspectorFieldEdit" in source
    assert "data-inspector-edit-key" in source
    assert "${renderInspectorFieldEditor(fieldKey)}" not in render_right
    assert "${renderInspectorCompareTools(fieldKey, fieldEntries)}" not in render_right
    assert "Formatting applies to the selected canvas text" in source


def test_right_inspector_lists_and_selects_editable_fields():
    source = _frontend_source()

    assert "inspectorFieldEntriesForSelection" in source
    assert "renderInspectorFieldList" in source
    assert "data-inspector-field-key" in source
    assert "selectInspectorField" in source
    assert "field-list" in source
    assert "inspector-field-row" in source


def test_field_reset_controls_are_kept_out_of_default_sidebar():
    source = _frontend_source()
    render_right = source[source.index("function renderRightInspector"):]

    assert "resetFieldByKey" in source
    assert "resetSelectedInspectorField" in source
    assert "data-inspector-reset-field-key" in source
    assert "inspectorResetSingleFieldBtn" in source
    assert "Reset selected field" not in render_right


def test_field_inspector_covers_core_page_types():
    source = _frontend_source()

    assert "cover.trip_title" in source
    assert "summary.trip_glance" in source
    assert "summary.journey_arc" in source
    assert "`days.${index}.${name}`" in source
    assert "`final_pages.whats_included_pages_html.${index}.html`" in source
    assert "`document_pages.${pageIndex}.manual_blocks.${blockIndex}.editable_fields.content_html`" in source
