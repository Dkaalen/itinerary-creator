from types import SimpleNamespace

from scripts.real_output_qa.repetition_checks import score_repetition


def _day(day: int, intro: str, leisure: str = "") -> SimpleNamespace:
    blocks = []
    if leisure:
        blocks.append(SimpleNamespace(kind="leisure", description=leisure))
    return SimpleNamespace(day=f"Day {day}", intro=intro, blocks=blocks)


def test_repetition_check_catches_same_intro_template_with_different_cities() -> None:
    days = [
        _day(1, "Explore Oslo at your own pace, with the rest of the day left open for independent time."),
        _day(2, "Explore Bergen at your own pace, with the rest of the day left open for independent time."),
        _day(3, "Explore Tromsø at your own pace, with the rest of the day left open for independent time."),
    ]
    issues = []

    score_repetition(issues, days)

    assert any(issue.code == "templated_day_intro_repetition" for issue in issues)


def test_repetition_check_catches_lightly_varied_leisure_copy() -> None:
    days = [
        _day(1, "Arrive in Oslo and settle in.", "The rest of the day is free to explore Oslo at your own pace."),
        _day(2, "Travel to Bergen by train.", "The rest of the day is free to explore Bergen at your own pace."),
        _day(3, "Continue north to Tromsø.", "The rest of the day is free to explore Tromsø at your own pace."),
    ]
    issues = []

    score_repetition(issues, days)

    assert any(issue.code == "repeated_leisure_copy" for issue in issues)


def test_repetition_check_leaves_distinct_day_copy_unflagged() -> None:
    days = [
        _day(1, "Arrive in Helsinki and transfer to your hotel before an evening at leisure."),
        _day(2, "Cross the Gulf of Finland for a self-guided day in Tallinn before returning by ferry."),
        _day(3, "Board the overnight train to Rovaniemi, with your private cabin reserved for the journey north."),
    ]
    issues = []

    score_repetition(issues, days)

    assert not any(issue.code == "templated_day_intro_repetition" for issue in issues)
