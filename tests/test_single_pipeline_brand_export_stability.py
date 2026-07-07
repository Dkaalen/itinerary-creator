from pathlib import Path
from tests.support.static_contracts import read_contract_text

from app_modules.export_stage_action import enter_export_stage


class _State(dict):
    pass


def test_export_stage_does_not_request_blocking_pdf_editor_commit():
    state = _State(
        {
            "app_stage": "pictures",
            "_pdf_after_visual_edit_commit_nonce": "stale-commit",
            "_visual_editor_export_commit_ready": False,
            "_visual_editor_commit_nonce": "stale-commit",
        }
    )
    result = enter_export_stage(state)

    assert result.ok is True
    assert state["app_stage"] == "export"
    assert state["_pdf_after_visual_edit_commit_nonce"] is None
    assert state["_visual_editor_export_commit_ready"] is False
    assert state["_visual_editor_commit_nonce"] is None


def test_generation_buttons_share_one_pipeline_and_only_set_brand():
    source = read_contract_text("app_modules/input_step.py")
    generation_source = read_contract_text("app_modules/generation_action.py")
    preview_source = read_contract_text("app_modules/generation_preview_builder.py")
    settings_source = read_contract_text("app_modules/generation_settings.py")

    assert "Generate agent itinerary" in source
    assert "Generate customer itinerary" in source
    assert source.count("generate_itinerary(st.session_state, raw_text)") == 1
    assert 'output_brand = "booknordics_customer" if generate_customer else "agent"' in source
    assert "requested_output_brand" in source

    assert "parse_and_normalize_itinerary(raw_text)" in generation_source
    assert generation_source.count("parse_and_normalize_itinerary(raw_text)") == 1
    assert generation_source.count("build_generation_preview_artifact(") == 1
    assert preview_source.count("build_itinerary_render_context(") == 1
    assert preview_source.count("build_itinerary_html_from_context(") == 1
    assert 'output_edits["output_brand"] = settings.output_brand' in settings_source


def test_pdf_export_screen_has_bounded_editor_commit_before_export():
    source = read_contract_text("app_modules/export_step.py")
    export_page_source = read_contract_text("app_modules/export_page.py")
    preflight_source = read_contract_text("app_modules/pdf_preflight.py")
    state_source = read_contract_text("app_modules/export_state.py")

    picture_source = read_contract_text("app_modules/picture_step.py")

    assert "Applying pending editor changes" not in source
    assert "the PDF must be created from the exact visible editor state" in picture_source
    assert "Create PDF from last saved version" in picture_source
    assert "request_pdf_creation_after_visual_editor_commit" not in source
    assert "clear_pdf_editor_commit_request" not in export_page_source
    assert "pending_editor_commit" not in preflight_source
    assert "pending_editor_commit" not in state_source
