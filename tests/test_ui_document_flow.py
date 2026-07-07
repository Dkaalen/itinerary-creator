from pathlib import Path
from tests.support.static_contracts import read_contract_text

from images.replacement_options import list_replacement_image_options_for_rows


def test_active_main_view_uses_locked_document_flow_without_old_steps():
    source = read_contract_text("app_modules/main_view.py")
    config_source = read_contract_text("app_modules/workflow_config.py")

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

    input_source = read_contract_text("app_modules/input_step.py")
    assert "Generate agent itinerary" in input_source
    assert "Generate customer itinerary" in input_source
    assert "Add pictures" in read_contract_text("app_modules/add_pictures_cta.py")
    assert "Create PDF" in read_contract_text("app_modules/picture_pdf_cta.py")
    assert "def render_export_page" in read_contract_text("app_modules/export_page.py")
    assert "enter_export_stage" in read_contract_text("app_modules/picture_pdf_cta.py")
    assert "request_pdf_commit_func=request_pdf_creation_after_visual_editor_commit" not in read_contract_text("app_modules/picture_step.py")


def test_edit_page_stops_duplicate_add_pictures_button_after_gateway_block():
    source = read_contract_text("app_modules/image_gateway_ui.py")
    edit_source = read_contract_text("app_modules/add_pictures_cta.py")

    assert "def _image_bank_gateway_is_blocking" in source
    assert "if _image_bank_gateway_is_blocking(gateway_result):" in edit_source
    assert "return" in edit_source[edit_source.index("if _image_bank_gateway_is_blocking(gateway_result):"):edit_source.index('if st.button("Add pictures"')]

def test_picture_page_hands_off_to_real_export_stage():
    picture_source = read_contract_text("app_modules/picture_step.py")
    cta_source = read_contract_text("app_modules/picture_pdf_cta.py")
    export_source = read_contract_text("app_modules/export_page.py")

    assert 'if st.button("Create PDF", type="primary", use_container_width=True):' in cta_source
    assert "enter_export_stage" in cta_source
    assert "enter_export_stage(st.session_state, auto_create_pdf=True)" in cta_source
    assert "request_pdf_commit_func=request_pdf_creation_after_visual_editor_commit" not in picture_source + cta_source
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


def test_styles_remove_legacy_header_without_sidebar_theme():
    styles = "\n".join(path.read_text() for path in Path("ui").glob("style_*.py"))

    assert "workflow-step-grid { display: none" not in styles
    assert "data-testid=\"stSidebar\"" not in styles
    assert ".document-stage-panel" in styles
    assert ".flow-nav" in styles
    assert "display: none !important" in styles


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
