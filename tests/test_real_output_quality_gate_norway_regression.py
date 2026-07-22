from __future__ import annotations

from pathlib import Path

from scripts.real_excel_fixture_bank import ExcelFixtureCandidate
from scripts.real_output_qa.rendering import render_candidate_review

FIXTURE = Path(__file__).resolve().parent / "fixtures/real_inputs/norway_winter_output_quality_regression.txt"


def _norway_review():
    raw_text = FIXTURE.read_text(encoding="utf-8")
    candidate = ExcelFixtureCandidate(
        workbook_path=Path("Norway Winter Output Quality Regression.txt"),
        sheet_name="norway_winter_quality",
        kind="regression",
        country_tags=("norway",),
        purpose_tags=("output_quality", "pdf_regression"),
        row_count=sum(1 for line in raw_text.splitlines() if line.strip().startswith("Day ")),
        day_count=8,
        raw_text=raw_text,
    )
    return render_candidate_review(candidate)


def test_norway_pdf_regression_uses_client_ready_summary_intro_and_leisure_copy() -> None:
    review = _norway_review()
    day_by_id = {day.day: day for day in review.days}
    issue_codes = {issue.code for issue in review.score.issues}
    journey_experiences = [item.get("experience", "") for item in review.journey_arc]

    assert review.score.error_count == 0
    assert "suspicious_am_pm_time_range" in issue_codes
    assert review.journey_title == "How Your Trip Unfolds"
    assert "arc" not in review.journey_title.lower()
    assert len(journey_experiences) == len(set(journey_experiences))
    assert "Norway in a Nutshell to Flåm" in journey_experiences
    assert "Norway in a Nutshell to Bergen" in journey_experiences

    day1 = day_by_id["Day 1"]
    assert "transfer and stay details" not in day1.intro.lower()
    assert "listed below" not in day1.intro.lower()
    assert "arranged transfer brings you to your accommodation" in day1.intro
    assert all("open for your own plans" not in text.lower() for text in day1.leisure)
    assert all("remaining time is best kept simple" not in text.lower() for day in review.days for text in day.leisure)


def test_norway_pdf_regression_keeps_broad_activity_titles_and_cleans_supplier_typos() -> None:
    review = _norway_review()
    day_by_id = {day.day: day for day in review.days}
    rendered_text = "\n".join(
        [
            review.trip_title,
            review.trip_subtitle,
            review.route,
            *(
                "\n".join((day.title, day.intro, *day.activities, *day.leisure))
                for day in review.days
            ),
            *review.included,
        ]
    )

    assert day_by_id["Day 5"].title == "Best of Bergen Private Walking Tour"
    assert day_by_id["Day 5"].decision_labels["title_decision_source"] == "activity_product_display_title"
    assert "narrow_inclusion_title" in day_by_id["Day 5"].decision_labels.get("title_decision_rejected_sources", "")
    assert "Fløibanen Funicular" not in day_by_id["Day 5"].title
    assert "Best of Bergen Private Walking Tour" in "\n".join(day_by_id["Day 5"].activities)

    assert day_by_id["Day 6"].title == "Tromsø Private City Tour & Private Northern Lights Tour by Minibus"
    assert day_by_id["Day 6"].decision_labels["title_decision_source"] == "schedule_composed_activity_title"
    assert "Tromsø Private City Tour" in "\n".join(day_by_id["Day 6"].activities)
    assert "Fjellheisen Cable Car" not in day_by_id["Day 6"].title
    assert "vehcile" not in rendered_text.lower()
    assert "private vehicle" in rendered_text.lower()
