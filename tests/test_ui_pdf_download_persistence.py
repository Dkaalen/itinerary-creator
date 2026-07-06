from pathlib import Path


def test_pdf_download_has_durable_top_and_bottom_stations():
    export_source = (
        Path("app_modules/export_step.py").read_text()
        + Path("app_modules/export_download_station.py").read_text()
    )
    artifact_source = Path("app_modules/export_pdf_artifacts.py").read_text()
    main_source = Path("app_modules/picture_step.py").read_text() + Path("app_modules/export_page.py").read_text()

    assert "current_pdf_artifact" in artifact_source
    assert "store_pdf_artifact" in artifact_source
    assert "def render_pdf_download_station" in export_source
    assert "render_pdf_download_station(location=\"bottom\")" in export_source
    assert "render_pdf_download_station(location=\"top\")" in main_source
    assert "key=f\"download_pdf_{location}\"" in export_source


def test_pdf_download_button_is_sticky_when_ready():
    styles = (Path("ui/style_export.py").read_text() + Path("ui/style_responsive.py").read_text())

    assert ".pdf-ready-panel" in styles
    assert "stDownloadButton" in styles
    assert "position: sticky" in styles
    assert "bottom: 1rem" in styles


def test_dirty_state_clears_durable_pdf_artifact():
    output_edits = Path("ui/output_edits.py").read_text()
    preview_rebuild = Path("app_modules/preview_rebuild.py").read_text()
    workflow_state = Path("app_modules/workflow_state.py").read_text()

    assert "st.session_state.export_pdf_bytes = None" in output_edits
    assert "st.session_state.export_pdf_signature = None" in output_edits
    assert "PDF_ARTIFACT_KEYS" in workflow_state
    assert "export_pdf_bytes" in workflow_state
    assert "export_pdf_signature" in workflow_state
    assert "mark_pdf_dirty_state(state" in preview_rebuild


def test_visual_editor_noop_saves_do_not_dirty_pdf():
    source = Path("visual_editor_component/editor_result_applier.py").read_text()

    assert "before_snapshot = _stable_output_edits_snapshot(output_edits)" in source
    assert "after_snapshot = _stable_output_edits_snapshot(output_edits)" in source
    assert "if mark_dirty and before_snapshot != after_snapshot" in source
