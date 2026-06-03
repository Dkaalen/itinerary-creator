import re
from pathlib import Path

from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from itinerary_generation.content_validator import validate_html
from itinerary_generation.day_intro_engine import create_day_intro
from itinerary_generation.exclusion_sections import create_whats_not_included
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.titles import create_day_title
from itinerary_generation.transport_safety import scan_client_output
from ui.render_helpers import clean_space
from ui.travel_sequence_blocks import build_travel_arrangements_block, is_travel_sequence_candidate


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def _fixture(name: str) -> str:
    return Path("tests/fixtures/stress_inputs/messy_transport_safety", name).read_text(encoding="utf-8")


def _travel_html(day_rows):
    travel_rows = [row for row in day_rows if is_travel_sequence_candidate(row)]
    block = build_travel_arrangements_block(travel_rows)
    return block["html"] if block else ""


def _plain(html: str) -> str:
    return clean_space(re.sub(r"<[^>]+>", " ", html).replace("&amp;", "&"))


def _section_items(sections, title):
    for section in sections:
        if section["title"] == title:
            return section["items"]
    return []


def test_levi_bus_station_is_terminal_not_destination_and_coach_details_are_clean():
    rows = _rows(_fixture("levi_transport_self_transfer.txt"))
    grouped = group_rows_by_day(rows)
    day5 = grouped["Day 5"]

    assert create_day_title(day5) == "Coach Transfer to Levi"
    intro = create_day_intro(day5, "Rich descriptive")
    assert "towards Levi today" in intro
    assert "Bus Station today" not in intro

    text = _plain(_travel_html(day5))
    assert "Coach Transfer from Rovaniemi Bus Station to Levi Bus Station" in text
    assert "Departure: 11:40 AM" in text
    assert "Arrival: 2:00 PM" in text
    assert "Duration: 2 hours 20 minutes" in text
    assert "Final timing will be confirmed in the travel documents." in text
    assert "levi Bus Station" not in text
    assert "relased" not in text
    assert not scan_client_output(text)


def test_self_transfer_supplier_wording_is_split_cleaned_and_excluded():
    rows = _rows(_fixture("levi_transport_self_transfer.txt"))
    grouped = group_rows_by_day(rows)
    day6 = grouped["Day 6"]

    html = _travel_html(day6)
    text = _plain(html)
    assert "Self-arranged transfer from Levin Iglut to Levi Nordic Star Igloos" in text
    assert "Private transfer may be requested locally at additional cost" in text
    for raw in ["self Transfer", "Pls", "tranfers", "addon cost", "paid on ground"]:
        assert raw not in text
    assert not scan_client_output(text)

    inclusions = create_categorized_inclusions(rows, grouped)
    included_text = "\n".join(item for section in inclusions for item in section["items"])
    assert "Self-arranged transfer from Levin Iglut" not in included_text

    exclusions = "\n".join(create_whats_not_included(rows))
    assert "Self-arranged transfer from Levin Iglut to Levi Nordic Star Igloos - 15th of January" in exclusions
    assert "Private transfer supplement, if requested locally" in exclusions
    for raw in ["Pls", "addon cost", "paid on ground", "tranfers"]:
        assert raw not in exclusions


def test_departure_transfer_preserves_explicit_kittila_airport():
    rows = _rows(_fixture("levi_transport_self_transfer.txt"))
    grouped = group_rows_by_day(rows)
    day7 = grouped["Day 7"]

    intro = create_day_intro(day7, "Rich descriptive")
    assert "Kittilä Airport" in intro
    assert "Levi Airport" not in intro
    assert "your hotel to your hotel" not in intro

    text = _plain(_travel_html(day7))
    assert "Private transfer from your hotel to Kittilä Airport" in text
    assert "Private Hotel to" not in text

    private_items = "\n".join(_section_items(create_categorized_inclusions(rows, grouped), "Private transfers"))
    assert "Private transfer from your hotel to Kittilä Airport." in private_items
    assert "Private Hotel to Kittilä Airport" not in private_items


def test_transport_firewall_flags_known_raw_leaks_and_validator_includes_them():
    bad_text = "self Transfer from Levin Iglut, Pls request at reception for private tranfers at addon cost to be paid on ground"
    findings = scan_client_output(bad_text)
    assert {finding.code for finding in findings} >= {"supplier_pls", "raw_addon_cost", "bad_transport_typo"}

    html_findings = validate_html(f"<section class='day-section'>{bad_text}</section>")
    codes = {finding.code for finding in html_findings}
    assert "raw_pls" in codes
    assert "raw_addon_cost" in codes
    assert "raw_transport_typo" in codes


def test_messy_transport_fixture_bank_is_present_for_future_regressions():
    fixture_dir = Path("tests/fixtures/stress_inputs/messy_transport_safety")
    names = {path.name for path in fixture_dir.glob("*.txt")}
    assert {
        "levi_transport_self_transfer.txt",
        "nordic_transport_variants.txt",
        "flight_typo_airport_codes.txt",
    }.issubset(names)
