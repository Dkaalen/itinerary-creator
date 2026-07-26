from pathlib import Path
from tests.support.static_contracts import read_contract_text


def test_pdf_download_has_durable_top_and_bottom_stations():
    export_source = (
        read_contract_text("app_modules/export_step.py")
        + read_contract_text("app_modules/export_download_station.py")
    )
    artifact_source = read_contract_text("app_modules/export_pdf_artifacts.py")
    main_source = read_contract_text("app_modules/picture_step.py") + read_contract_text("app_modules/export_page.py")

    assert "current_pdf_artifact" in artifact_source
    assert "store_pdf_artifact" in artifact_source
    assert "def render_pdf_download_station" in export_source
    assert "render_pdf_download_station(location=\"bottom\")" in export_source
    assert "render_pdf_download_station(location=\"top\")" in main_source
    assert "key=f\"download_pdf_{location}\"" in export_source


def test_pdf_download_button_is_sticky_when_ready():
    styles = (read_contract_text("ui/style_export.py") + read_contract_text("ui/style_responsive.py"))

    assert ".pdf-ready-panel" in styles
    assert "stDownloadButton" in styles
    assert "position: sticky" in styles
    assert "bottom: 1rem" in styles


def test_dirty_state_clears_durable_pdf_artifact():
    output_edits = read_contract_text("ui/output_edits.py")
    preview_rebuild = read_contract_text("app_modules/preview_rebuild.py")
    render_lifecycle = read_contract_text("app_modules/render_lifecycle.py")

    assert "st.session_state.export_pdf_bytes = None" in output_edits
    assert "st.session_state.export_pdf_signature = None" in output_edits
    assert "from app_modules.pdf_artifact_state import clear_pdf_artifact_state" in render_lifecycle
    assert "clear_pdf_artifact_state(state, status=status)" in render_lifecycle
    assert "mark_pdf_dirty_state(state" in preview_rebuild


def test_visual_editor_noop_saves_do_not_dirty_pdf():
    source = read_contract_text("visual_editor_component/editor_result_applier.py")

    assert "before_snapshot = _stable_output_edits_snapshot(output_edits)" in source
    assert "after_snapshot = _stable_output_edits_snapshot(output_edits)" in source
    assert "if mark_dirty and before_snapshot != after_snapshot" in source
