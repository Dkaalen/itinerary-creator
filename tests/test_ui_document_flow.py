from pathlib import Path

from images.replacement_options import list_replacement_image_options_for_rows


def test_active_main_view_uses_locked_document_flow_without_old_steps():
    source = Path("app_modules/main_view.py").read_text()
    config_source = Path("app_modules/workflow_config.py").read_text()

    assert 'FLOW_STAGES = ("input", "edit", "pictures", "export")' in config_source
    assert '"input": "Paste text"' in config_source
    assert '"edit": "Edit itinerary"' in config_source
    assert '"pictures": "Add pictures"' in config_source
    assert '"export": "Create PDF"' in config_source

    assert "st.sidebar" not in source
    assert "render_sidebar_controls" not in source
    assert "render_workflow_overview" not in source
    assert "with st.expander(\"1 —" not in source
    assert "Step 1" not in source
    assert "Step 2" not in source
    assert "Step 3" not in source
    assert "Step 4" not in source
    assert "Step 5" not in source

    assert "Generate Itinerary" in Path("app_modules/input_step.py").read_text()
    assert "Add pictures" in Path("app_modules/preview_step.py").read_text()
    assert "Create PDF" in Path("app_modules/picture_step.py").read_text()
    assert "def render_export_page" in Path("app_modules/export_page.py").read_text()
    assert "enter_export_stage" in Path("app_modules/picture_step.py").read_text()
    assert "request_pdf_commit_func=request_pdf_creation_after_visual_editor_commit" in Path("app_modules/picture_step.py").read_text()


def test_edit_page_stops_duplicate_add_pictures_button_after_gateway_block():
    source = Path("app_modules/image_gateway_ui.py").read_text()
    edit_source = Path("app_modules/preview_step.py").read_text()

    assert "def _image_bank_gateway_is_blocking" in source
    assert "if _image_bank_gateway_is_blocking(gateway_result):" in edit_source
    assert "return" in edit_source[edit_source.index("if _image_bank_gateway_is_blocking(gateway_result):"):edit_source.index('if st.button("Add pictures"')]

def test_picture_page_hands_off_to_real_export_stage():
    picture_source = Path("app_modules/picture_step.py").read_text()
    export_source = Path("app_modules/export_page.py").read_text()

    assert 'if st.button("Create PDF", type="primary", use_container_width=True):' in picture_source
    assert "enter_export_stage" in picture_source
    assert "request_pdf_commit_func=request_pdf_creation_after_visual_editor_commit" in picture_source
    assert "render_export_step(app_version)" not in picture_source

    assert "render_pdf_download_station(location=\"top\")" in export_source
    assert "render_export_step(app_version)" in export_source
    assert "_render_document_editor(pictures_active=True)" in export_source


def test_removed_duplicate_visual_editor_app_shells_stay_deleted():
    removed = (
        Path("visual_editor_component/app_modules/main_view.py"),
        Path("visual_editor_component/app_modules/export_step.py"),
        Path("visual_editor_component/app_modules/workflow_shell.py"),
    )

    assert all(not path.exists() for path in removed)


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
