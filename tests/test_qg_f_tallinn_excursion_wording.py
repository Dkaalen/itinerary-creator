from generator import group_rows_by_day
from itinerary_generation.content_validator import compact_html
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from text_polish import polish_client_text
from ui.day_blocks import build_day_blocks


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def _day_text(raw: str, day: str = "Day 1") -> str:
    rows = _rows(raw)
    grouped = group_rows_by_day(rows)
    return compact_html("\n".join(block["html"] for block in build_day_blocks(grouped[day]) if block))


def test_self_guided_tallinn_excursion_does_not_imply_guided_sightseeing():
    raw = """
Day 1	Activity	01/06/2026							Helsinki	Excursion to Tallinn - Round Trip Ferry tickets to Tallin - Self guided tour of Old Town Tallinn - Time: 10:30 am - 07:30 pm Cruise Duration 2 Hr
"""
    text = _day_text(raw)

    assert "exploring the historic Old Town at your own pace" in text
    assert "Guided sightseeing is shown separately" not in text
    assert "guided Old Town experience" not in text


def test_guided_tallinn_excursion_mentions_guided_old_town_without_internal_note():
    raw = """
Day 1	Activity	01/06/2026							Helsinki	Excursion to Tallinn - Round Trip Ferry tickets to Tallin - guided tour of Old Town Tallinn walking TOur ( 2-3 Hrs ) - Time: 10:30 am - 07:30 pm Cruise Duration 2 Hr
"""
    text = _day_text(raw)

    assert "guided Old Town experience" in text
    assert "Guided sightseeing is shown separately" not in text
    assert "at your own pace" not in text


def test_ferry_only_tallinn_excursion_uses_neutral_old_town_wording():
    raw = """
Day 1	Activity	01/06/2026							Helsinki	Excursion to Tallinn - Departure from Helsinki: 10:30 am - Return from Tallinn: 7:30 pm - Ferry tickets included
"""
    text = _day_text(raw)

    assert "historic Old Town before returning to Helsinki" in text
    assert "guided" not in text.lower()
    assert "at your own pace" not in text


def test_free_time_tallinn_excursion_uses_self_guided_wording():
    raw = """
Day 1	Activity	01/06/2026							Helsinki	Excursion to Tallinn - Round Trip Ferry tickets - free time in Tallinn Old Town - Time: 10:30 am - 07:30 pm Cruise Duration 2 Hr
"""
    text = _day_text(raw)

    assert "exploring the historic Old Town at your own pace" in text
    assert "Self-guided time in Tallinn" in text
    assert "guided tour" not in text.lower()


def test_generated_text_repairs_hlesinki_typo():
    assert polish_client_text("Cross from Hlesinki to Tallinn") == "Cross from Helsinki to Tallinn"
    assert polish_client_text("Return to Hlesinkih after the ferry") == "Return to Helsinki after the ferry"
