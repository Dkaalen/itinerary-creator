from copy import deepcopy

from itinerary_generation.copy_sequence import apply_copy_sequence_plan
from itinerary_generation.render_model import RenderBlock, RenderDay, RenderDocument


def _day(number: int, intro: str, *, source: str = "full_leisure_intro", title: str = "Leisure") -> RenderDay:
    return RenderDay(
        day=f"Day {number}",
        number=str(number),
        city="Rovaniemi",
        title=title,
        intro=intro,
        labels={"intro_decision_source": source, "intro_manual_override": "false"},
        blocks=[RenderBlock(kind="leisure", description="Any open time in Rovaniemi is left flexible for your own plans.")],
    )


def test_itinerary_sequence_varies_only_repeatable_generic_copy_deterministically():
    document = RenderDocument(days=[
        _day(1, "A full day is left open in Rovaniemi, with no arranged activities competing for your time."),
        _day(2, "A full day is left open in Rovaniemi, with no arranged activities competing for your time."),
        _day(3, "A full day is left open in Rovaniemi, with no arranged activities competing for your time."),
    ])
    left = apply_copy_sequence_plan(deepcopy(document))
    right = apply_copy_sequence_plan(deepcopy(document))

    assert [day.intro for day in left.days] == [day.intro for day in right.days]
    assert len({day.intro for day in left.days}) == 3
    assert len({day.blocks[0].description for day in left.days}) == 3


def test_manual_and_strong_product_copy_are_never_rewritten():
    manual = _day(1, "My manual wording")
    manual.labels["intro_manual_override"] = "true"
    overnight = _day(
        2,
        "Spend the night in a Crystal Lavvo while looking for the Northern Lights.",
        source="activity_day_intro",
        title="Crystal Lavvo Overnight Stay",
    )
    document = RenderDocument(days=[manual, overnight, deepcopy(overnight)])

    apply_copy_sequence_plan(document)

    assert document.days[0].intro == "My manual wording"
    assert document.days[1].intro == document.days[2].intro
