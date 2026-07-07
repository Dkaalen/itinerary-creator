from __future__ import annotations

from types import SimpleNamespace

from scripts.preview_pdf_text_guard import build_text_guard_report
from scripts.promote_real_output_regression import build_regression_record, write_regression_record
from scripts.review_real_output_text import build_markdown_report, build_reviews
from scripts.score_real_output_text import build_score_report
from scripts.tag_real_excel_fixture_bank import build_tag_index, derive_candidate_tags
from scripts.real_excel_fixture_bank import build_candidate_index
from scripts.real_output_text_quality import score_rendered_output
from scripts.update_real_output_qa_index import build_qa_index, markdown_index

FIXTURE_ID = "Standard-Itinerary-Finland.xlsx::106"
TYPO_FIXTURE_ID = "Standard-Itinerary-Iceland.xlsx::8D RW"


def test_real_output_review_runner_builds_readable_markdown() -> None:
    reviews = build_reviews(sample_size=1, seed=63, fixture_ids=[FIXTURE_ID])

    assert len(reviews) == 1
    review = reviews[0]
    markdown = build_markdown_report(reviews, seed=63, sample_size=1)

    assert FIXTURE_ID in markdown
    assert "Trip title:" in markdown
    assert "### Days" in markdown
    assert "Source rows:" in markdown
    assert "Transport:" in markdown
    assert "Accommodation:" in markdown
    assert "Optional experiences:" in markdown
    assert review.trip_title
    assert review.days


def test_output_scoring_flags_known_text_quality_issues_from_fake_context() -> None:
    day = SimpleNamespace(day="Day 1", title="Arrival", city="NOK", intro="Today is open for independent time in NOK.", blocks=[])
    context = SimpleNamespace(
        trip_title="Centraly Located Adventure",
        trip_subtitle="Supplier typo proof",
        destinations_line="Oslo · NOK · Shuttle transfer",
        journey_arc=[],
        whats_included=["Free wifi"],
        optional_addons=[{"day": "Day 1", "title": "Raw Optional - Time: 09:00 - Meeting point: Lobby"}],
        whats_not_included=[],
        render_document=SimpleNamespace(route="Oslo · NOK · Shuttle transfer", days=[day], warnings=[]),
    )

    score = score_rendered_output([], context, source_text="3/4-star hotel")
    codes = {issue.code for issue in score.issues}

    assert not score.ok
    assert "supplier_typo_leaked" in codes
    assert "raw_optional_supplier_blob" in codes
    assert "currency_code_used_as_city" in codes
    assert "route_contains_service_as_destination" in codes


def test_seeded_output_score_report_is_deterministic() -> None:
    first = build_score_report(sample_size=3, seed=6200)
    second = build_score_report(sample_size=3, seed=6200)

    assert first["selected_fixture_ids"] == second["selected_fixture_ids"]
    assert first["average_score"] == second["average_score"]


def test_activity_upgrade_typo_fixture_no_longer_errors() -> None:
    report = build_score_report(sample_size=1, seed=7007, fixture_ids=[TYPO_FIXTURE_ID])
    codes = {issue["code"] for issue in report["reviews"][0]["score"]["issues"]}

    assert report["error_count"] == 0
    assert "typoed_activity_type_seen" not in codes
    assert "route_contains_service_as_destination" not in codes


def test_regression_promotion_writes_json(tmp_path) -> None:
    record = build_regression_record(
        fixture_id=TYPO_FIXTURE_ID,
        seed=7007,
        name="activity upgrade typo classification",
        issue_code="typoed_activity_type_seen",
        expected_behavior="Activity Upgrade rows must not become destinations.",
    )
    path = write_regression_record(record, tmp_path)

    assert path.exists()
    assert record["fixture_id"] == TYPO_FIXTURE_ID
    assert record["expected_behavior"]
    assert record["day_excerpt"]


def test_preview_pdf_text_guard_reads_render_facing_text() -> None:
    report = build_text_guard_report(fixture_ids=[FIXTURE_ID], sample_size=1, seed=66)

    assert report["sample_size"] == 1
    assert report["fixtures"][0]["char_count"] > 100
    assert report["error_count"] == 0


def test_fixture_tagging_and_qa_index_are_deterministic() -> None:
    candidates = build_candidate_index()
    candidate = next(item for item in candidates if item.fixture_id == FIXTURE_ID)
    tags = derive_candidate_tags(candidate)
    tag_index = build_tag_index(candidates[:3])
    qa_index = build_qa_index(sample_size=2, seed=6200)
    markdown = markdown_index(qa_index)

    assert "finland" in tags
    assert tag_index["candidate_count"] == 3
    assert qa_index["score_report"]["selected_fixture_ids"]
    assert "# Real Output QA Index" in markdown
