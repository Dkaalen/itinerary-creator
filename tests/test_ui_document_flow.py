from pathlib import Path

from images.replacement_options import list_replacement_image_options_for_rows


def test_active_main_view_uses_locked_document_flow_without_old_steps():
    source = Path("app_modules/main_view.py").read_text()

    assert 'FLOW_STAGES = ("input", "edit", "pictures", "export")' in source
    assert '"input": "Paste text"' in source
    assert '"edit": "Edit itinerary"' in source
    assert '"pictures": "Add pictures"' in source
    assert '"export": "Create PDF"' in source

    assert "st.sidebar" not in source
    assert "render_sidebar_controls" not in source
    assert "render_workflow_overview" not in source
    assert "with st.expander(\"1 —" not in source
    assert "Step 1" not in source
    assert "Step 2" not in source
    assert "Step 3" not in source
    assert "Step 4" not in source
    assert "Step 5" not in source

    assert "Generate Itinerary" in source
    assert "Add pictures" in source
    assert "Create PDF" in source
    assert "def render_export_page" in source
    assert "request_pdf_creation_after_visual_editor_commit()" in source


def test_picture_page_hands_off_to_real_export_stage():
    source = Path("app_modules/main_view.py").read_text()

    picture_start = source.index("def render_picture_page")
    export_start = source.index("def render_export_page")
    picture_source = source[picture_start:export_start]
    export_source = source[export_start:source.index("def render_debug_tools")]

    assert 'if st.button("Create PDF", type="primary", use_container_width=True):' in picture_source
    assert '_set_stage("export")' in picture_source
    assert "render_export_step(app_version)" not in picture_source

    assert "render_pdf_download_station(location=\"top\")" in export_source
    assert "render_export_step(app_version)" in export_source
    assert "_render_document_editor(pictures_active=True)" in export_source


def test_removed_duplicate_visual_editor_app_shells_are_shims():
    duplicate_main = Path("visual_editor_component/app_modules/main_view.py").read_text()
    duplicate_export = Path("visual_editor_component/app_modules/export_step.py").read_text()
    duplicate_workflow = Path("visual_editor_component/app_modules/workflow_shell.py").read_text()

    assert "compatibility shim" in duplicate_main.lower()
    assert "compatibility shim" in duplicate_export.lower()
    assert "compatibility shim" in duplicate_workflow.lower()
    assert "st.sidebar" not in duplicate_main
    assert "1 — Import" not in duplicate_main
    assert "render_export_step" in duplicate_export
    assert "workflow-step-grid" not in duplicate_workflow


def test_styles_do_not_hide_legacy_workflow_or_force_sidebar_theme():
    styles = Path("ui/styles.py").read_text()

    assert "workflow-step-grid { display: none" not in styles
    assert "data-testid=\"stSidebar\"" not in styles
    assert ".document-stage-panel" in styles


def test_replacement_options_do_not_show_default_only_bank(tmp_path):
    default_dir = tmp_path / "image_bank" / "Default"
    default_dir.mkdir(parents=True)
    (default_dir / "Default_Summer_Fjord_01.webp").write_bytes(b"placeholder")

    options = list_replacement_image_options_for_rows(
        "Day 1",
        [{"day": "Day 1", "city": "Bergen", "title": "Walking tour"}],
        image_bank_scan_paths=[tmp_path / "image_bank"],
    )

    assert options == []
