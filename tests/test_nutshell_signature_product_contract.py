from __future__ import annotations

from images.matcher_context import build_day_context
from images.matcher_scoring import score_image_for_day
from images.metadata import ImageCandidate
from itinerary_domain.nutshell_model import NutshellJourney, NutshellLeg
from itinerary_generation.journey_overview_evidence import chapter_experience
from itinerary_generation.transport_domain.nutshell_render import build_featured_nutshell_block


def _row(*, timed: bool = False) -> dict:
    legs = (
        NutshellLeg(origin="Oslo", destination="Myrdal", mode="train", departure_time="08:00" if timed else ""),
        NutshellLeg(origin="Myrdal", destination="Flåm", mode="train", arrival_time="13:00" if timed else ""),
    )
    journey = NutshellJourney(
        origin="Oslo",
        destination="Bergen",
        client_title="Norway in a Nutshell to Bergen",
        route_points=("Oslo", "Myrdal", "Flåm", "Gudvangen", "Voss", "Bergen"),
        legs=legs,
    )
    return {
        "row_id": "nin-1",
        "day": "Day 3",
        "type": "Transport",
        "effective_type": "Transport",
        "city": "Bergen",
        "title": journey.client_title,
        "details": "Norway in a Nutshell scenic rail and fjord journey",
        "activity_product": {"domain_contract": journey.as_metadata},
    }


def _candidate(city: str, filename: str, themes=(), tokens=()) -> ImageCandidate:
    return ImageCandidate(
        path=f"/bank/Norway/{city}/{filename}.webp",
        country="Norway",
        city=city,
        filename=f"{filename}.webp",
        themes=tuple(themes),
        tokens=tuple(tokens),
        seasons=("summer",),
    )


def test_journey_arc_keeps_canonical_signature_product_name() -> None:
    assert chapter_experience([_row()], "Bergen") == "Norway in a Nutshell to Bergen"


def test_untimed_nutshell_route_is_not_repeated_as_timeline() -> None:
    block = build_featured_nutshell_block([_row()], [], travel_row_lines_func=lambda row: [])
    assert block is not None
    assert [section.title for section in block.extra_sections].count("Route") == 1
    assert "Journey timeline" not in [section.title for section in block.extra_sections]


def test_timed_nutshell_legs_still_render_a_timeline() -> None:
    block = build_featured_nutshell_block([_row(timed=True)], [], travel_row_lines_func=lambda row: [])
    assert block is not None
    assert "Journey timeline" in [section.title for section in block.extra_sections]


def test_signature_collection_is_reserved_and_prioritized() -> None:
    context = build_day_context("Day 3", [_row()])
    signature = _candidate("Norway in a Nutshell", "flam-railway-naeroyfjord", ("train", "fjord"), ("nutshell", "flam", "fjord"))
    bergen = _candidate("Bergen", "bergen-harbour", ("city", "waterfront"), ("bergen", "harbour"))
    signature_score, _ = score_image_for_day(signature, context)
    bergen_score, _ = score_image_for_day(bergen, context)
    assert signature_score > bergen_score

    unrelated = build_day_context("Day 4", [{"type": "Activity", "city": "Bergen", "title": "Bergen walking tour"}])
    blocked_score, reasons = score_image_for_day(signature, unrelated)
    assert blocked_score == 0
    assert any("protected Norway in a Nutshell" in reason for reason in reasons)


def test_oslofjord_image_is_blocked_for_nutshell_day() -> None:
    context = build_day_context("Day 3", [_row()])
    oslofjord = _candidate("Oslo", "oslofjord-sightseeing-cruise", ("fjord", "waterfront"), ("oslofjord", "cruise"))
    score, reasons = score_image_for_day(oslofjord, context)
    assert score == 0
    assert any("Oslofjord image blocked" in reason for reason in reasons)
