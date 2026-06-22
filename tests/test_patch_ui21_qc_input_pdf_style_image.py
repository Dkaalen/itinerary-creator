from pathlib import Path

from app_modules.export_state import export_readiness_from_state
from app_modules.pdf_preflight import build_pdf_preflight_report
from images.image_match_audit import ImageAuditWarning
from images.image_workflow_review import build_image_workflow_review
from itinerary_generation.input_review import build_structured_input_review, format_structured_input_review
from itinerary_generation.itinerary_health_checks import build_itinerary_health_issues, summarize_itinerary_health_issues
from visual_editor_component.style_presets import default_theme_preset, preset_class_map, style_preset_registry, theme_presets


READY_IMAGE_BANK = {"full_bank_found": True, "missing_full_bank": False, "destination_image_count": 4}


def test_qc1_health_checks_find_actionable_review_items_without_ui():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo", "commercial_status": "included"},
        {"day": "Day 2", "type": "Transfer", "effective_type": "Transfer", "city": "Bergen", "commercial_status": "included"},
    ]

    issues = build_itinerary_health_issues(rows, parser_diagnostics=[{"category": "typo", "message": "Possible typo"}])
    summary = summarize_itinerary_health_issues(issues)

    assert any(issue.code == "missing_hotel_name" and issue.severity == "critical" for issue in issues)
    assert any(issue.code == "missing_transfer_route" for issue in issues)
    assert any(issue.source == "parser_diagnostics" for issue in issues)
    assert summary.status_label == "Needs review"


def test_input1_structured_review_summarizes_route_counts_and_issues():
    rows = [
        {"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo", "hotel_name": "The Thief", "commercial_status": "included"},
        {"day": "Day 2", "type": "Activity", "effective_type": "Activity", "city": "Bergen", "title": "Bryggen walk", "commercial_status": "included"},
    ]

    review = build_structured_input_review(rows)
    text = format_structured_input_review(review)

    assert review.day_count == 2
    assert review.service_counts["Hotel"] == 1
    assert review.route == ("Oslo", "Bergen")
    assert review.status_label == "Clear"
    assert "Structured Input Review" in text


def test_pdf1_preflight_feeds_export_readiness():
    state = {
        "itinerary_html": "<html></html>",
        "parsed_rows": [{"day": "Day 1", "type": "Hotel", "effective_type": "Hotel", "city": "Oslo", "commercial_status": "included"}],
        "output_edits": {"pictures_added": True},
        "preview_signature": "sig",
    }

    preflight = build_pdf_preflight_report(state, READY_IMAGE_BANK)
    readiness = export_readiness_from_state(state, READY_IMAGE_BANK)

    assert preflight.status_label == "Needs review"
    assert any(issue.code == "missing_hotel_name" for issue in preflight.issues)
    assert readiness.can_create_pdf is False
    assert readiness.preflight_status == "Needs review"
    assert any("hotel" in message.lower() for message in readiness.preflight_issues)


def test_style1_registry_has_theme_and_new_pdf_safe_presets_synced_to_frontend():
    registry = style_preset_registry()
    js = Path("visual_editor_component/frontend/js/style_presets.js").read_text(encoding="utf-8")

    assert preset_class_map("text_styles")["premium_callout"] == "ve-text-premium-callout"
    assert preset_class_map("colors")["deep_teal"] == "ve-color-deep-teal"
    assert theme_presets()
    assert default_theme_preset()["id"] == registry["themes"][0]["id"]
    assert "ve-text-premium-callout" in js
    assert "nordic_luxury" in js


def test_img1_workflow_review_reports_image_coverage_and_errors():
    grouped_days = {"Day 1": [{}], "Day 2": [{}]}
    matches = {"Day 1": {"path": "/bank/oslo.jpg"}}
    warnings = [ImageAuditWarning(code="bad", message="Bad image", severity="error", day="Day 1")]

    review = build_image_workflow_review(grouped_days, matches, warnings)

    assert review.required_days == 2
    assert review.matched_days == 1
    assert review.unmatched_days == ("Day 2",)
    assert review.error_count == 1
    assert review.status_label == "Needs review"
    assert review.as_dict()["coverage_text"] == "1/2 days matched"


def test_ui21_default_inspector_stays_canvas_first_without_sidebar_text_editor():
    inspector_js = Path("visual_editor_component/frontend/js/editor_inspector.js").read_text(encoding="utf-8")
    render_start = inspector_js.index("function renderRightInspector()")
    render_end = inspector_js.index("function updateRightInspector()")
    render_body = inspector_js[render_start:render_end]

    assert "renderInspectorTextTools" in render_body
    assert "renderInspectorImageTools" in render_body
    assert "renderInspectorFieldEditor" not in render_body
    assert "renderInspectorCompareTools" not in render_body
    assert "renderSourceRows" not in render_body
