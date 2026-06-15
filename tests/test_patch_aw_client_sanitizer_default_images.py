from __future__ import annotations

from pathlib import Path
from PIL import Image

from app_modules.itinerary_render_context import build_itinerary_render_context
from images.day_image_selection import select_day_images_with_overrides
from itinerary_generation.client_sanitizer import contains_price_or_currency, normalize_important_note_paragraphs, sanitize_client_text
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.quality_gate import evaluate_client_output_quality, render_document_text
from itinerary_generation.render_model import RenderDocument, RenderFinalPage, RenderFinalSection
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


GROUP_TOUR_WITH_PRICES = """
Day 1	Transfer 	01/10/2026							Reykjavik	Shuttle/FLybus  Airport to City Centre 
Day 1	Hotel	01/10/2026	02/10/2026					Reykjavik	3 Star , Fosshotel Raudara  , 1xNight , 1xStandard Double Room, Incl Brekafast 
Day 2	Day overview	02/10/2026							Reykjavik	"Reykjavík: 6-Day Holiday Package Ring Road Tour & Blue Lagoon |9 AM | 6 DAY GROUP TOUR STARTS  Overview
What's included?
Pick-up/drop-off in central Reykjavik
Knowledgeable, English-speaking guide
5 nights hotel accommodation incl. breakfast
Day 1: The Golden Circle and South Coast
Day 2: The South Coast and Jökulsarlon
Day 3: Eastern Iceland and Egilsstadir
Day 4: The North-East and Akureyri
Day 5: Western Iceland and Laugarbakki
Day 6: Western Iceland and Blue Lagoon

NOT INCLUDED 
Flights to/from Keflavik Airport (KEF)
Private transfers from/to the airport
Food and drinks except hotel breakfasts
Optional Katla Ice Cave tour (206€/person)
Optional Vök Baths entrance (55€/person)
Optional Whale Watching tour (96€/person)
Personal health and travel insurances
Single traveler supplement fee 395€"
Day 2	Activity	02/10/2026							SOUTH COAST	"Day 1: Explore the Golden Circle & South Coast
Visit Þingvellir National Park, Geysir, Gullfoss, Seljalandsfoss and Skógafoss."
Day 3	Activity	03/10/2026							Höfn	"Day 2: Discover Glaciers, Ice Caves & Diamond Beach
Visit Vík, the Katla Ice Cave, Jökulsárlón Glacier Lagoon and Diamond Beach."
Day 6	Activity	06/10/2026							Laugarbakki	"Day 5: Spot Whales & Explore Historic Sites
Start your day with Whale Watching before continuing to Laugarbakki."
Day 7	Activity	07/10/2026							Reykjavik	"Day 6: Hike Craters, See Waterfalls & Relax at Blue Lagoon
Return to Reykjavík via waterfalls before relaxing at the Blue Lagoon."
Day 7	Hotel	07/10/2026	08/10/2026					Reykjavik	3 Star ,Center Hotels Skjaldbreið, 1xNight , 1xStandard Double Room, Incl Brekafast 
Day 8	Transfer 	08/10/2026								Shuttle / Flybus : City centre to Airport
"""


def _rows():
    return normalize_itinerary_rows(parse_itinerary(GROUP_TOUR_WITH_PRICES))


def _write_webp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 20), (80, 120, 40)).save(path, format="WEBP")


def test_patch_aw_sanitizer_removes_prices_but_keeps_optional_labels():
    text = "Optional Katla Ice Cave tour (206€/person), Optional Vök Baths entrance (55€/person), single traveler supplement fee 395€"

    cleaned = sanitize_client_text(text)

    assert "206" not in cleaned
    assert "55" not in cleaned
    assert "395" not in cleaned
    assert "€" not in cleaned
    assert "Optional Katla Ice Cave tour" in cleaned
    assert "Optional Vök Baths entrance" in cleaned


def test_patch_aw_quality_gate_blocks_price_or_currency_leak():
    document = RenderDocument(final_sections=[RenderFinalSection("x", "X", pages=[RenderFinalPage(items=["Optional cave tour 206€/person"])])])

    report = evaluate_client_output_quality(document)

    assert report.is_blocked
    assert any(issue.code == "client_price_or_currency_leak" for issue in report.blocking_issues)


def test_patch_aw_group_tour_output_has_no_prices_or_raw_programme_heading_leaks():
    rows = _rows()
    context = build_itinerary_render_context(rows, group_rows_by_day(rows), {"pictures_added": False})
    text = render_document_text(context.render_document)

    assert not contains_price_or_currency(text)
    assert "206" not in text
    assert "395" not in text
    assert "The golden circle and south coast" not in text
    assert "The south coast and Jökulsárlón" not in text
    assert "Guided 6-day Iceland programme" in text


def test_patch_aw_optional_group_tour_extra_is_not_rendered_as_included():
    rows = _rows()
    day6 = next(row for row in rows if row.get("day") == "Day 6" and row.get("effective_type") == "Activity")
    assert day6.get("group_tour_optional_extra") is True

    context = build_itinerary_render_context(rows, group_rows_by_day(rows), {"pictures_added": False})
    day6_render = next(day for day in context.render_document.days if day.day == "Day 6")
    whale_block = next(block for block in day6_render.blocks if block.kind == "group_tour_day")

    assert not any("Whale Watching" in item for item in whale_block.includes)
    included_text = "\n".join(
        item
        for section in context.render_document.final_sections
        if section.title == "What’s included"
        for page in section.pages
        for render_section in page.sections
        for item in render_section.items
    )
    assert "Whale Watching - 6th of October" not in included_text


def test_patch_aw_important_notes_are_real_paragraphs_not_fragments():
    fragments = [
        "Transport schedules",
        "including flights",
        "trains",
        "buses",
        "are subject to operational changes.",
        "Activities may be weather dependent",
        "and can be adjusted if required.",
    ]

    paragraphs = normalize_important_note_paragraphs(fragments)

    assert paragraphs == [
        "Transport schedules including flights trains buses are subject to operational changes.",
        "Activities may be weather dependent and can be adjusted if required.",
    ]


def test_patch_aw_default_only_bank_returns_no_auto_final_images(tmp_path):
    bank = tmp_path / "image_bank"
    _write_webp(bank / "Default" / "Default_Autumn_City_01.webp")
    grouped = {"Day 1": [{"day": "Day 1", "city": "Reykjavík", "title": "Welcome to Reykjavík"}]}

    matches = select_day_images_with_overrides(grouped, {}, app_root=tmp_path, image_bank_scan_paths=[bank])

    assert matches == {"Day 1": None}


def test_patch_aw_preview_image_contract_contains_bank_status(tmp_path):
    bank = tmp_path / "image_bank_full"
    image = bank / "Iceland" / "Reykjavik" / "Reykjavik_Autumn_City_01.webp"
    _write_webp(image)
    grouped = {"Day 1": [{"day": "Day 1", "city": "Reykjavík", "title": "Welcome to Reykjavík"}]}

    matches = select_day_images_with_overrides(grouped, {}, app_root=tmp_path, image_bank_scan_paths=[bank])

    assert matches["Day 1"]
    assert matches["Day 1"]["image_bank_status"]["full_bank_found"] is True
    assert matches["Day 1"]["source_type"] == "full_bank"
