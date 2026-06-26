from pathlib import Path

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
    calls = []

    result = enter_export_stage(state, request_pdf_commit_func=lambda: calls.append("called"))

    assert result.ok is True
    assert state["app_stage"] == "export"
    assert calls == []
    assert state["_pdf_after_visual_edit_commit_nonce"] is None
    assert state["_visual_editor_export_commit_ready"] is False
    assert state["_visual_editor_commit_nonce"] is None


def test_generation_buttons_share_one_pipeline_and_only_set_brand():
    source = Path("app_modules/input_step.py").read_text(encoding="utf-8")
    generation_source = Path("app_modules/generation_action.py").read_text(encoding="utf-8")

    assert "Generate Agent Itinerary" in source
    assert "Generate Customer Itinerary" in source
    assert source.count("generate_itinerary(st.session_state, raw_text)") == 1
    assert 'output_brand = "booknordics_customer" if generate_customer else "agent"' in source
    assert "requested_output_brand" in source

    assert "parse_and_normalize_itinerary(raw_text)" in generation_source
    assert generation_source.count("parse_and_normalize_itinerary(raw_text)") == 1
    assert generation_source.count("build_itinerary_render_context(") == 1
    assert generation_source.count("build_itinerary_html_from_context(") == 1
    assert "output_edits[\"output_brand\"] = output_brand" in generation_source


def test_pdf_export_screen_has_no_unbounded_pending_editor_wait():
    source = Path("app_modules/export_step.py").read_text(encoding="utf-8")
    export_page_source = Path("app_modules/export_page.py").read_text(encoding="utf-8")
    preflight_source = Path("app_modules/pdf_preflight.py").read_text(encoding="utf-8")
    state_source = Path("app_modules/export_state.py").read_text(encoding="utf-8")

    assert "Applying pending editor changes" not in source
    assert "visual_editor_export_commit_ready" not in source
    assert "request_pdf_creation_after_visual_editor_commit" not in source
    assert export_page_source.index("clear_pdf_editor_commit_request") < export_page_source.index("_render_document_editor")
    assert "pending_editor_commit" not in preflight_source
    assert "pending_commit = False" in state_source
