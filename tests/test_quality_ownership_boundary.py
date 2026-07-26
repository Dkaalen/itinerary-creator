from __future__ import annotations

import ast
from pathlib import Path

import app_modules.itinerary_render_context as render_context_module
import itinerary_generation.client_quality_report as quality_report_module
from app_modules import pdf_export_blockers
from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.render_context_cache import get_cached_render_context, store_render_context
from itinerary_generation.client_output_quality_gate import add_image_quality_issues
from itinerary_generation.client_quality_report import build_client_output_quality_report
from itinerary_generation.generation_quality_gate import ItineraryValidationIssue
from itinerary_generation.health_report import build_itinerary_health_report, format_itinerary_health_report
from itinerary_generation.quality_row_selection import (
    as_quality_rows,
    is_important_quality_row,
    select_important_rows,
)
from scripts.real_output_qa import scoring

ROOT = Path(__file__).resolve().parents[1]


def _function_names(relative_path: str) -> set[str]:
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    return {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def test_quality_row_selection_has_one_owner():
    retired_names = {"_as_rows", "_is_important_row", "_important_rows"}
    assert not (_function_names("itinerary_generation/generation_quality_gate.py") & retired_names)
    assert not (_function_names("itinerary_generation/health_report.py") & retired_names)

    generation_source = (ROOT / "itinerary_generation/generation_quality_gate.py").read_text(encoding="utf-8")
    health_source = (ROOT / "itinerary_generation/health_report.py").read_text(encoding="utf-8")
    assert "from itinerary_generation.quality_row_selection import" in generation_source
    assert "from itinerary_generation.quality_row_selection import" in health_source


def test_quality_row_selection_preserves_order_identity_and_duplicate_rows():
    duplicate_a = {"day": "Day 1", "type": "Activity", "title": "Same product", "source_row": 10}
    duplicate_b = {"day": "Day 1", "type": "Activity", "title": "Same product", "source_row": 11}
    ignored = {"day": "Day 1", "type": "Note", "title": "Internal note"}
    malformed = "not a row"

    rows = as_quality_rows([duplicate_a, malformed, ignored, duplicate_b])
    selected = select_important_rows(rows)

    assert rows == [duplicate_a, ignored, duplicate_b]
    assert selected == [duplicate_a, duplicate_b]
    assert selected[0] is duplicate_a
    assert selected[1] is duplicate_b
    assert is_important_quality_row(duplicate_a)
    assert not is_important_quality_row(ignored)


def test_advisor_assessment_is_calculated_once_per_report(monkeypatch):
    calls = 0
    original = quality_report_module.assess_advisor_readiness

    def counted(issues):
        nonlocal calls
        calls += 1
        return original(issues)

    monkeypatch.setattr(quality_report_module, "assess_advisor_readiness", counted)
    report = quality_report_module.build_client_output_quality_report(
        [ItineraryValidationIssue("warning", "weak_generic_fallback", "Needs review")]
    )

    assert calls == 1
    assert report.advisor_rating == "Minor edit"
    assert report.advisor_assessment.rating == "Minor edit"
    assert report.advisor_assessment.reasons == ("Needs review",)
    assert calls == 1


def test_render_context_evaluates_quality_once_and_preview_reuses_report(monkeypatch):
    calls = 0
    original = render_context_module.evaluate_prepared_client_output_quality

    def counted(document, *, source_rows=None):
        nonlocal calls
        calls += 1
        return original(document, source_rows=source_rows)

    monkeypatch.setattr(render_context_module, "evaluate_prepared_client_output_quality", counted)
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Oslo",
            "title": "Hotel Oslo",
            "hotel_name": "Hotel Oslo",
            "commercial_status": "included",
        }
    ]
    context = render_context_module.build_itinerary_render_context(rows, {"Day 1": rows}, {})

    assert calls == 1
    assert context.client_quality_report is not None
    build_itinerary_html_from_context(context)
    assert calls == 1


def test_cached_render_context_keeps_the_same_quality_report_instance():
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "City walk",
            "details": "A guided city walk.",
            "commercial_status": "included",
        }
    ]
    context = render_context_module.build_itinerary_render_context(rows, {"Day 1": rows}, {})
    state = {}

    store_render_context(state, signature="quality-signature", context=context)
    cached = get_cached_render_context(state, signature="quality-signature")

    assert cached is context
    assert cached.client_quality_report is context.client_quality_report


def test_image_findings_extend_prepared_report_without_rerunning_document_rules(monkeypatch):
    base = build_client_output_quality_report(
        [ItineraryValidationIssue("warning", "weak_generic_fallback", "Review copy")]
    )
    monkeypatch.setattr(
        "itinerary_generation.client_output_quality_gate._image_match_issues",
        lambda _images: [ItineraryValidationIssue("error", "missing_day_image", "Image missing")],
    )
    monkeypatch.setattr(
        "itinerary_generation.client_output_quality_gate._image_bank_status_issues",
        lambda _status: [],
    )

    extended = add_image_quality_issues(base, day_images={}, image_bank_status={})

    assert base.advisor_rating == "Minor edit"
    assert extended.advisor_rating == "Unusable"
    assert [issue.code for issue in extended.issues] == ["weak_generic_fallback", "missing_day_image"]


def test_pdf_readiness_adds_image_findings_to_prepared_report(monkeypatch):
    prepared = build_client_output_quality_report([])
    captured = {}

    def add_images(report, *, day_images=None, image_bank_status=None):
        captured["report"] = report
        captured["day_images"] = day_images
        captured["image_bank_status"] = image_bank_status
        return report

    monkeypatch.setattr(pdf_export_blockers, "add_image_quality_issues", add_images)
    context = type("Context", (), {"client_quality_report": prepared})()

    blocked = pdf_export_blockers.client_safety_blocks_pdf(
        context,
        {"Day 1": {"path": "oslo.jpg"}},
        {"status": "ready"},
        clear_pdf_artifact=lambda _reason: None,
    )

    assert blocked is False
    assert captured == {
        "report": prepared,
        "day_images": {"Day 1": {"path": "oslo.jpg"}},
        "image_bank_status": {"status": "ready"},
    }


def test_real_output_qa_reuses_prepared_report(monkeypatch):
    report = build_client_output_quality_report(
        [ItineraryValidationIssue("error", "internal_copy_leak", "Internal copy leaked")]
    )
    context = type("Context", (), {"client_quality_report": report})()

    def fail(*_args, **_kwargs):
        raise AssertionError("prepared quality report should be reused")

    monkeypatch.setattr(scoring, "evaluate_client_output_quality", fail)
    assert scoring._client_quality_report(context, []) is report

    issues = []
    scoring._score_client_truth_contracts(issues, report)
    assert [issue.code for issue in issues] == ["internal_copy_leak"]


def test_score_rendered_output_reuses_context_report(monkeypatch):
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "City walk",
            "details": "Explore Oslo on foot.",
            "commercial_status": "included",
        }
    ]
    context = render_context_module.build_itinerary_render_context(rows, {"Day 1": rows}, {})

    def fail(*_args, **_kwargs):
        raise AssertionError("real-output QA should reuse the prepared report")

    monkeypatch.setattr(scoring, "evaluate_client_output_quality", fail)
    result = scoring.score_rendered_output(rows, context)

    assert result.advisor_rating == context.client_quality_report.advisor_rating
    assert result.advisor_reasons == context.client_quality_report.advisor_assessment.reasons


def test_health_report_reuses_prepared_advisor_assessment():
    client_report = build_client_output_quality_report(
        [ItineraryValidationIssue("warning", "serious_copy_repetition", "Repeated introductions")]
    )
    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Oslo",
            "title": "City walk",
            "commercial_status": "included",
        }
    ]

    health = build_itinerary_health_report(rows, client_quality_report=client_report)

    assert health.advisor_rating == "Major edit"
    assert health.status == "Needs review"
    assert any("Advisor quality — Major edit" in warning for warning in health.warnings)
    assert "Advisor quality: Major edit" in format_itinerary_health_report(health)


def test_preview_pdf_and_qa_do_not_recompute_prepared_quality_report():
    html_source = (ROOT / "app_modules/itinerary_html.py").read_text(encoding="utf-8")
    pdf_source = (ROOT / "app_modules/pdf_export_blockers.py").read_text(encoding="utf-8")
    scoring_source = (ROOT / "scripts/real_output_qa/scoring.py").read_text(encoding="utf-8")
    diagnostics_source = (ROOT / "ui/diagnostics_panel.py").read_text(encoding="utf-8")

    assert "evaluate_client_output_quality(" not in html_source
    assert "evaluate_client_output_quality(" not in pdf_source
    assert "add_image_quality_issues(" in pdf_source
    assert "client_quality_report = _client_quality_report(context, rows)" in scoring_source
    assert scoring_source.count("evaluate_client_output_quality(") == 1  # fallback for non-prepared QA contexts only
    assert "client_quality_report=getattr(render_context, \"client_quality_report\", None)" in diagnostics_source
