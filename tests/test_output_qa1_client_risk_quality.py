from types import SimpleNamespace

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.day_intro_engine import create_day_intro
from itinerary_generation.quality_gate import evaluate_client_output_quality
from itinerary_generation.render_model import RenderBlock, RenderDay, RenderDocument
from itinerary_generation.transport_safety import scan_client_output
from parser_modules.parser_main import parse_itinerary
from text_polish import polish_client_text


def test_output_qa1_departure_intro_respects_self_arranged_airport_transfer():
    rows = parse_itinerary(
        "\n".join(
            [
                "Day 1\tTransfer\t27.09.2026\t\tOslo: Self transfer to Oslo Airport",
                "Day 1\tDeparture\t27.09.2026\t\tOslo: Departure home",
            ]
        )
    )

    intro = create_day_intro(rows, "Rich descriptive")

    assert "make your own way to Oslo Airport" in intro
    assert "arranged transfer" not in intro


def test_output_qa1_polishes_meeting_point_quotes_and_hype_removal_grammar():
    meeting = polish_client_text("Platform E, behind Fisketorget by ‘’TROLLCRUISE’’ sign")
    description = polish_client_text("Our electric, luxurious boat lets you enjoy this tranquil fjord landscape in silence.")
    inclusion = polish_client_text("Boat tour aboard & luxurious catamaran")

    assert meeting == "Platform E, behind Fisketorget by the “TROLLCRUISE” sign"
    assert "electric boat lets" in description
    assert "electric, boat" not in description
    assert inclusion == "Boat tour aboard a catamaran"


def test_output_qa1_suspicious_am_pm_time_is_visible_in_review_scans():
    findings = scan_client_output("Fjord cruise — Gudvangen → Flåm · 12:10 AM - 2:10 PM")

    assert any(finding.code == "suspicious_am_pm_time_range" for finding in findings)


def test_output_qa1_client_output_quality_warns_on_suspicious_time_ranges():
    document = RenderDocument(
        days=[
            RenderDay(
                day="Day 9",
                number="9",
                city="Oslo",
                title="Norway in a Nutshell to Oslo",
                intro="Rail and fjord journey.",
                blocks=[RenderBlock(kind="travel_sequence", lines=["Fjord cruise — Gudvangen → Flåm · 12:10 AM - 2:10 PM"])],
            )
        ]
    )

    report = evaluate_client_output_quality(document)

    assert not report.is_blocked
    assert any(issue.code == "suspicious_am_pm_time_range" for issue in report.warnings)


def test_copy1_and_output_qa1_render_context_has_less_stale_day_intros():
    rows = parse_itinerary(
        "\n".join(
            [
                "Day 1\tActivity\t19.09.2026\t\tOslo: Fjord Sightseeing Cruise onboard Electric Boat - Time: 11:00 am - 01:00 pm - Meeting point: Platform E, behind Fisketorget by ‘’TROLLCRUISE’’ sign - Includes: Electric fjord cruise with audio guidance",
                "Day 2\tActivity\t23.09.2026\t\tStavanger: Lysefjord & Preikestolen Fjord Cruise - Time: 12:30 pm - 4:30 pm - Includes: Sustainable, quiet & scenic fjord cruise - Description: Discover magical Lysefjord and Preikestolen (Pulpit Rock).",
                "Day 3\tActivity\t21.09.2026\t\tKristiansand: Guided Kayaking on the Otra River - Time: 11:00 am - 2:00 pm - Includes: Professional guide",
            ]
        )
    )
    context = build_itinerary_render_context(rows, group_rows_by_day(rows), {})
    intros = {day.city: day.intro for day in context.render_document.days}

    assert "See Oslo from the fjord today" in intros["Oslo"]
    assert "The day centres on Lysefjord" in intros["Stavanger"]
    assert "See Kristiansand from river level" in intros["Kristiansand"]
    assert not any(intro.startswith("Sail from") for intro in intros.values())
