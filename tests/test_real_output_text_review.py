from __future__ import annotations

from scripts.review_real_output_text import build_markdown_report, build_reviews
from scripts.score_real_output_text import build_score_report

FIXTURE_ID = "Standard-Itinerary-Finland.xlsx::106"


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


def test_output_scoring_flags_known_real_text_quality_issues() -> None:
    report = build_score_report(sample_size=1, seed=64, fixture_ids=[FIXTURE_ID])
    review = report["reviews"][0]
    codes = {issue["code"] for issue in review["score"]["issues"]}

    assert report["sample_size"] == 1
    assert review["score"]["score"] < 100
    assert "supplier_typo_leaked" in codes
    assert "raw_optional_supplier_blob" in codes


def test_seeded_output_score_report_is_deterministic() -> None:
    first = build_score_report(sample_size=3, seed=6200)
    second = build_score_report(sample_size=3, seed=6200)

    assert first["selected_fixture_ids"] == second["selected_fixture_ids"]
    assert first["average_score"] == second["average_score"]
