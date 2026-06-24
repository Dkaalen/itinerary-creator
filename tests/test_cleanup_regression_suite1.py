import json
import sys
import types
from pathlib import Path

from tests.frontend_asset_helpers import read_resolved_frontend_css

streamlit_stub = types.SimpleNamespace(
    warning=lambda *args, **kwargs: None,
    success=lambda *args, **kwargs: None,
    session_state={},
    components=types.SimpleNamespace(
        v1=types.SimpleNamespace(declare_component=lambda *args, **kwargs: (lambda **component_kwargs: None))
    ),
)
sys.modules.setdefault("streamlit", streamlit_stub)
sys.modules.setdefault("streamlit.components", streamlit_stub.components)
sys.modules.setdefault("streamlit.components.v1", streamlit_stub.components.v1)

from app_modules.export_state import export_readiness_from_state
from itinerary_generation.render_document_builder import build_render_document
from visual_editor_component.editor_workflow import apply_visual_editor_result


READY_IMAGE_BANK = {
    "full_bank_found": True,
    "missing_full_bank": False,
    "destination_image_count": 12,
}


def test_cleanup_suite_export_path_has_no_legacy_qa_gate_or_picture_review_gate():
    readiness = export_readiness_from_state(
        {
            "itinerary_html": "<html></html>",
            "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Arrival"}],
            "output_edits": {"pictures_added": True},
            "image_review_error_count": 99,
            "preview_signature": "sig-1",
        },
        READY_IMAGE_BANK,
    )

    assert readiness.can_create_pdf is True
    assert readiness.status_label == "Ready to create"
    assert not hasattr(readiness, "picture_review_ready")

    export_source = Path("app_modules/export_step.py").read_text(encoding="utf-8")
    state_source = Path("app_modules/export_state.py").read_text(encoding="utf-8")
    assert "Client QA" not in export_source
    assert "QA report" not in export_source
    assert "picture_review_ready" not in state_source


def test_cleanup_suite_preview_final_pages_are_render_document_owned():
    html_source = Path("app_modules/itinerary_html.py").read_text(encoding="utf-8")

    assert "render_final_sections_html_by_id(context.render_document.final_sections)" in html_source
    assert "create_whats_included" not in html_source
    assert "create_whats_not_included" not in html_source
    assert "ordered_page_ids" in html_source


def test_cleanup_suite_return_visit_copy_is_itinerary_level():
    rows = [
        {"day": "Day 1", "type": "Arrival", "effective_type": "Arrival", "city": "Oslo", "title": "Arrival in Oslo", "details": "Private transfer to hotel"},
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo", "title": "Check in", "details": "One-night stay."},
        {"day": "Day 2", "type": "Transfer", "effective_type": "Transfer", "city": "Bergen", "title": "Travel from Oslo to Bergen", "details": "Train from Oslo to Bergen."},
        {"day": "Day 3", "type": "Arrival", "effective_type": "Arrival", "city": "Oslo", "title": "Arrival in Oslo", "details": "Private transfer to hotel"},
        {"day": "Day 3", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo", "title": "Check in", "details": "One-night stay."},
    ]
    grouped = {"Day 1": rows[:2], "Day 2": rows[2:3], "Day 3": rows[3:]}

    document = build_render_document(rows, grouped)
    intros = {day.day: day.intro for day in document.days}
    titles = {day.day: day.title for day in document.days}

    assert titles["Day 1"] == "Welcome to Oslo"
    assert titles["Day 3"] == "Return to Oslo"
    assert intros["Day 1"].startswith("Welcome to Oslo.")
    assert intros["Day 3"].startswith("Return to Oslo.")
    assert "first impressions" not in intros["Day 3"].lower()


def test_cleanup_suite_image_only_editor_save_does_not_dirty_text():
    streamlit_stub.session_state = {}
    output_edits = {
        "days": {
            "Day 1": {
                "intro": "Generated Oslo intro",
                "intro_manual_override": False,
                "blocks_html": "<div>Generated body</div>",
                "blocks_manual_override": False,
            }
        }
    }

    result = json.dumps({"days": [{"day": "Day 1", "image": {"mode": "manual", "crop_focus": "center"}}]})

    assert apply_visual_editor_result(result, output_edits)
    day = output_edits["days"]["Day 1"]
    assert day["intro"] == "Generated Oslo intro"
    assert day["intro_manual_override"] is False
    assert day["blocks_html"] == "<div>Generated body</div>"
    assert day["blocks_manual_override"] is False
    assert output_edits["day_images"]["Day 1"]["mode"] == "manual"
    assert output_edits["day_images"]["Day 1"]["crop_focus"] == "center"


def test_cleanup_suite_editor_checks_are_canvas_first_without_client_qa_copy():
    editor_source = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "visual_editor_component/frontend/js/render.js",
            "visual_editor_component/frontend/js/editor_readiness.js",
            "visual_editor_component/frontend/js/images.js",
        )
    )
    editor_source += "\n" + read_resolved_frontend_css()

    assert "Document checks" in editor_source
    assert "Export checks" in editor_source
    assert "Ready for client" not in editor_source
    assert "Client QA" not in editor_source
    assert "client-risk" not in editor_source
    assert "hover an image to edit it on the canvas" in editor_source
    assert ".image-stage:hover .image-actions" in editor_source
