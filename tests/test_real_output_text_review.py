from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.preview_pdf_text_guard import build_text_guard_report
from scripts.promote_real_output_regression import build_regression_record, write_regression_record
from scripts.review_real_output_text import build_markdown_report, build_reviews, select_candidates
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


def test_seeded_output_selection_is_deterministic() -> None:
    # Broad real-output rendering is covered by CLI validation. This unit test
    # keeps the selection contract fast and deterministic inside pytest.
    from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST

    first_selection = [candidate.fixture_id for candidate in select_candidates(manifest_path=DEFAULT_MANIFEST, sample_size=3, seed=6200)]
    second_selection = [candidate.fixture_id for candidate in select_candidates(manifest_path=DEFAULT_MANIFEST, sample_size=3, seed=6200)]

    assert first_selection == second_selection
    assert len(first_selection) == 3


def test_activity_upgrade_typo_fixture_no_longer_errors() -> None:
    from parser_modules.effective_type_detection import detect_effective_type

    assert detect_effective_type("Actvity Upgrade", "Optional glacier hike", "Optional add-on") == "Activity Upgrade"


def test_regression_promotion_writes_json(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_score = SimpleNamespace(issues=(), to_dict=lambda: {"score": 100, "error_count": 0, "warning_count": 0})
    fake_review = SimpleNamespace(
        fixture={"fixture_id": TYPO_FIXTURE_ID},
        score=fake_score,
        trip_title="Iceland Adventure",
        trip_subtitle="A winter route",
        route="Reykjavík · South Coast",
        days=(
            SimpleNamespace(
                day="Day 1",
                title="Arrival in Reykjavík",
                city="Reykjavík",
                intro="Arrive and settle in.",
                transport=("Airport transfer",),
                activities=("Optional upgrade",),
                leisure=(),
                optional_experiences=(),
            ),
        ),
    )
    monkeypatch.setattr("scripts.promote_real_output_regression.build_reviews", lambda **_: (fake_review,))

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


def test_preview_pdf_text_guard_reads_render_facing_text(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_review = SimpleNamespace(
        fixture={"fixture_id": FIXTURE_ID},
        trip_title="Finland Winter Journey",
        trip_subtitle="A winter journey",
        route="Helsinki · Rovaniemi",
        days=[
            SimpleNamespace(
                day="Day 1",
                title="Arrival in Helsinki",
                city="Helsinki",
                intro="Arrive in Helsinki and settle into the journey.",
                transport=("Airport transfer",),
                accommodation=("Hotel in Helsinki",),
                activities=("Guided city walk",),
                leisure=("Time between arrangements",),
                optional_experiences=(),
            )
        ],
        included=("Accommodation",),
        optional_addons=(),
        not_included=("Flights",),
    )
    monkeypatch.setattr("scripts.preview_pdf_text_guard.build_reviews", lambda **_: (fake_review,))

    report = build_text_guard_report(fixture_ids=[FIXTURE_ID], sample_size=1, seed=66)

    assert report["sample_size"] == 1
    assert report["fixtures"][0]["char_count"] > 100
    assert report["error_count"] == 0


def test_fixture_tagging_and_qa_index_are_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    candidates = build_candidate_index()
    candidate = next(item for item in candidates if item.fixture_id == FIXTURE_ID)
    tags = derive_candidate_tags(candidate)
    tag_index = build_tag_index(candidates[:3])
    monkeypatch.setattr(
        "scripts.update_real_output_qa_index.build_score_report",
        lambda **_: {
            "seed": 6200,
            "selected_fixture_ids": [FIXTURE_ID],
            "sample_size": 1,
            "error_count": 0,
            "warning_count": 0,
            "average_score": 100,
            "reviews": [],
        },
    )
    qa_index = build_qa_index(sample_size=2, seed=6200)
    markdown = markdown_index(qa_index)

    assert "finland" in tags
    assert tag_index["candidate_count"] == 3
    assert qa_index["score_report"]["selected_fixture_ids"]
    assert "# Real Output QA Index" in markdown
