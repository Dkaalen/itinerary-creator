from generator import group_rows_by_day
from itinerary_generation.day_intro_engine import create_day_intro
from app_modules.itinerary_render_context import build_itinerary_render_context
from parser_modules.parser_main import parse_itinerary


def test_copy1_direct_day_intro_uses_premium_service_specific_copy():
    rows = parse_itinerary(
        "Day 1\tActivity\t23.09.2026\t\tStavanger: Lysefjord & Preikestolen Fjord Cruise - Time: 12:30 pm - 4:30 pm - Description: Discover Lysefjord and Preikestolen."
    )

    intro = create_day_intro(rows)

    assert "The day centres on Lysefjord" in intro
    assert intro.startswith("Sail from") is False


def test_copy1_planner_context_uses_same_less_stale_activity_copy():
    rows = parse_itinerary(
        "\n".join(
            [
                "Day 1\tActivity\t19.09.2026\t\tOslo: Fjord Sightseeing Cruise onboard Electric Boat - Time: 11:00 am - 01:00 pm - Meeting point: Platform E, behind Fisketorget by ‘’TROLLCRUISE’’ sign",
                "Day 2\tActivity\t21.09.2026\t\tKristiansand: Guided Kayaking on the Otra River - Time: 11:00 am - 2:00 pm - Includes: Professional guide",
            ]
        )
    )

    context = build_itinerary_render_context(rows, group_rows_by_day(rows), {})
    intros = {day.city: day.intro for day in context.render_document.days}

    assert "See Oslo from the fjord today" in intros["Oslo"]
    assert "See Kristiansand from river level" in intros["Kristiansand"]
    assert not any(intro.startswith("Sail from") for intro in intros.values())


def test_copy1_departure_copy_respects_self_arranged_transfer():
    rows = parse_itinerary(
        "\n".join(
            [
                "Day 10\tTransfer\t27.09.2026\t\tOslo: Self transfer to Oslo Airport",
                "Day 10\tDeparture\t27.09.2026\t\tOslo: Departure home",
            ]
        )
    )

    intro = create_day_intro(rows, "Rich descriptive")

    assert "make your own way to Oslo Airport" in intro
    assert "arranged transfer" not in intro
