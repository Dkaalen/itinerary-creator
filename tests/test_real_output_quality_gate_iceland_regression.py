from __future__ import annotations

from pathlib import Path

from generator import group_rows_by_day
from images.matcher_context import build_day_context
from itinerary_generation.activity_location_contract import activity_location_facts
from itinerary_generation.copy.activity_composition import client_activity_intro
from itinerary_generation.journey_overview_brain import create_journey_overview
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from parser_modules.time_normalize import normalize_time_text
from scripts.real_excel_fixture_bank import ExcelFixtureCandidate
from scripts.real_output_qa.rendering import render_candidate_review

FIXTURE = Path(__file__).resolve().parent / "fixtures/real_inputs/iceland_hub_excursion_output_quality_regression.txt"


def _raw_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _rows() -> list[dict]:
    return normalize_itinerary_rows(parse_itinerary(_raw_text()))


def _review():
    raw_text = _raw_text()
    candidate = ExcelFixtureCandidate(
        workbook_path=Path("Iceland Hub Excursion Output Quality Regression.txt"),
        sheet_name="iceland_hub_excursion_quality",
        kind="regression",
        country_tags=("iceland",),
        purpose_tags=("output_quality", "pdf_regression", "journey_overview"),
        row_count=sum(1 for line in raw_text.splitlines() if line.strip().startswith("Day ")),
        day_count=8,
        raw_text=raw_text,
    )
    return render_candidate_review(candidate)


def _rendered_text(review) -> str:
    return "\n".join(
        [
            review.trip_title,
            review.trip_subtitle,
            review.route,
            review.journey_title,
            *(f"{item.get('chapter', '')} {item.get('days', '')} {item.get('experience', '')}" for item in review.journey_arc),
            *("\n".join((day.title, day.intro, *day.activities, *day.leisure)) for day in review.days),
            *review.included,
            *review.not_included,
        ]
    )


def test_iceland_regression_scores_clean_after_real_output_quality_rebuild() -> None:
    review = _review()
    issue_codes = {issue.code for issue in review.score.issues}
    rendered_text = _rendered_text(review)

    assert review.score.error_count == 0
    assert review.score.warning_count == 0
    assert "malformed_client_time" not in issue_codes
    assert "unsupported_intro_theme" not in issue_codes
    assert "journey_overview_collapsed_hub_stay" not in issue_codes
    assert "banned_generated_phrase" not in issue_codes
    assert "raw supplier notes" not in rendered_text.casefold()
    assert "without exposing" not in rendered_text.casefold()
    assert "00:00 AM" not in rendered_text
    assert "15:00 PM" not in rendered_text
    assert "9. 00" not in rendered_text
    assert "otherwordly" not in rendered_text.casefold()


def test_iceland_journey_overview_uses_hub_and_spoke_chapters_not_one_random_highlight() -> None:
    grouped = group_rows_by_day(_rows())
    overview = create_journey_overview(grouped)
    experiences = [item["experience"] for item in overview]

    assert overview == [
        {"chapter": "Reykjavík", "days": "1", "experience": "Arrival and Reykjavík welcome"},
        {"chapter": "Reykjavík", "days": "2", "experience": "Whale watching and Blue Lagoon"},
        {"chapter": "Reykjavík", "days": "3 - 7", "experience": "Iceland day-trip highlights from Reykjavík"},
        {"chapter": "Keflavík", "days": "8", "experience": "Departure from Keflavík"},
    ]
    assert "Snæfellsnes Peninsula highlights" not in experiences


def test_iceland_intro_copy_is_supported_by_same_day_activity_facts() -> None:
    review = _review()
    day_by_id = {day.day: day for day in review.days}

    assert "Whale Watching" in day_by_id["Day 2"].intro
    assert "Blue Lagoon" in day_by_id["Day 2"].intro
    assert "volcano" not in day_by_id["Day 2"].intro.casefold()

    assert "Fagradalsfjall" in day_by_id["Day 6"].intro
    assert "Meradalir" in day_by_id["Day 6"].intro
    assert "Blue Lagoon" not in day_by_id["Day 6"].intro

    direct_blue_lagoon = client_activity_intro(
        "Blue Lagoon Admission",
        "Reykjavík",
        "Blue Lagoon admission and return transfer from Reykjavík",
    )
    direct_volcano = client_activity_intro(
        "Fagradalsfjall & Meradalir Volcano Hike",
        "Reykjavík",
        "Fagradalsfjall Meradalir volcano hike with hotel pick-up",
    )
    assert "volcano" not in direct_blue_lagoon.casefold()
    assert "Blue Lagoon" not in direct_volcano


def test_iceland_dotted_time_parsing_and_include_cleanup_preserve_supplier_times() -> None:
    assert normalize_time_text("Depart to Blue Lagoon from 9.00am to 5.00pm") == "Depart to Blue Lagoon from 9:00 AM to 5:00 PM"
    assert normalize_time_text("Return to Reykjavík from 1. 15:00 PM to 8. 15:00 PM") == "Return to Reykjavík from 1:15 PM to 8:15 PM"

    rows = _rows()
    blue_lagoon_row = next(row for row in rows if row.get("title") == "Blue Lagoon Admission")
    assert "Depart to Blue Lagoon from 9:00 AM to 5:00 PM" in blue_lagoon_row.get("includes", [])
    assert "Return to Reykjavík from 1:15 PM to 8:15 PM" in blue_lagoon_row.get("includes", [])

    review = _review()
    rendered_text = _rendered_text(review)
    assert "Depart to Blue Lagoon from 9:00 AM to 5:00 PM" in rendered_text


def test_iceland_activity_location_contract_separates_base_city_from_excursion_place() -> None:
    rows = _rows()
    by_title = {str(row.get("title", "")): row for row in rows if str(row.get("effective_type") or row.get("type")) == "Activity"}

    golden = activity_location_facts(by_title["Grand Golden Circle Full-Day Tour"])
    south = activity_location_facts(by_title["South Coast, Glacier & Black Sand Beach Tour"])
    jokulsarlon = activity_location_facts(by_title["Jökulsárlón Glacial Lagoon & Boat Tour"])

    assert golden.base_city == "Reykjavík"
    assert golden.excursion_region == "Golden Circle"
    assert golden.is_excursion
    assert "Gullfoss" in golden.attraction_places
    assert south.excursion_region == "Iceland’s South Coast"
    assert "Reynisfjara" in south.attraction_places
    assert jokulsarlon.excursion_region == "Jökulsárlón Glacier Lagoon"
    assert "glacier_lagoon" in jokulsarlon.image_intents


def test_iceland_image_context_uses_excursion_intents_not_only_reykjavik_city_context() -> None:
    grouped = group_rows_by_day(_rows())
    day3_context = build_day_context("Day 3", grouped["Day 3"])
    day4_context = build_day_context("Day 4", grouped["Day 4"])
    day6_context = build_day_context("Day 6", grouped["Day 6"])
    day7_context = build_day_context("Day 7", grouped["Day 7"])

    assert day3_context["city"] == "Golden Circle"
    assert "golden_circle" in day3_context["service_intents"]
    assert day4_context["city"] == "Iceland’s South Coast"
    assert "south_coast" in day4_context["service_intents"]
    assert day6_context["city"] == "Fagradalsfjall and Meradalir"
    assert "volcano_hike" in day6_context["service_intents"]
    assert day7_context["city"] == "Jökulsárlón Glacier Lagoon"
    assert "glacier_lagoon" in day7_context["service_intents"]
