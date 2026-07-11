from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST
from scripts.real_output_qa.selection import build_reviews


FIXTURE_ID = "Standard-Itinerary-Norway.xlsx::204"


def _review():
    return build_reviews(
        manifest_path=DEFAULT_MANIFEST,
        sample_size=1,
        seed=0,
        fixture_ids=[FIXTURE_ID],
    )[0]


def test_norway_204_uses_distinct_source_backed_arctic_intros():
    review = _review()
    day_6 = next(day for day in review.days if day.day == "Day 6")
    day_8 = next(day for day in review.days if day.day == "Day 8")

    assert "Crystal Lavvo" in day_6.intro
    assert "overnight" in day_6.intro
    assert "Visit to Sorrisniva Igloo Hotel" in day_8.intro
    assert "Northern Lights Hunt" in day_8.intro
    assert day_6.intro != day_8.intro


def test_norway_204_real_output_gate_has_no_repeated_intro_warning():
    review = _review()
    assert review.score.error_count == 0
    assert not any(issue.code == "repeated_day_intro" for issue in review.score.issues)


def test_iceland_self_drive_prefers_drive_route_over_local_rental_transfer():
    review = build_reviews(
        manifest_path=DEFAULT_MANIFEST,
        sample_size=1,
        seed=0,
        fixture_ids=["Calculation-template-DK0801.xlsx::Kalk 5"],
    )[0]
    day_3 = next(day for day in review.days if day.day == "Day 3")

    assert "Self transfer" not in day_3.intro
    assert "Reykjavík" in day_3.intro
    assert "Asborgir" in day_3.intro
    assert not any(issue.code == "transfer_phrase_treated_as_place" for issue in review.score.issues)


def test_norway_207_photography_days_keep_distinct_product_identity():
    review = build_reviews(
        manifest_path=DEFAULT_MANIFEST,
        sample_size=1,
        seed=0,
        fixture_ids=["Standard-Itinerary-Norway.xlsx::207"],
    )[0]
    day_7 = next(day for day in review.days if day.day == "Day 7")
    day_8 = next(day for day in review.days if day.day == "Day 8")

    assert "Reine" in day_7.intro
    assert "Henningsvær" in day_8.intro
    assert day_7.intro != day_8.intro
    assert not any(issue.code == "repeated_day_intro" for issue in review.score.issues)


def test_norway_calculator_kalk_2_keeps_kayak_summary_source_backed():
    review = build_reviews(
        manifest_path=DEFAULT_MANIFEST,
        sample_size=1,
        seed=0,
        fixture_ids=["Calculation-template-DK0807.xlsx::Kalk 2"],
    )[0]

    experiences = [item.get("experience", "") for item in review.journey_arc]
    assert any("Nærøyfjord kayaking" in item for item in experiences)
    assert not any("Otra River" in item for item in experiences)
    assert not any(issue.code == "unsupported_journey_overview_fact" for issue in review.score.issues)
    assert not any(issue.code == "activity_city_mismatch" for issue in review.score.issues)
