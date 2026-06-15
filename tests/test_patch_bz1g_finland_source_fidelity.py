"""Patch BZ1G gates for the Helsinki–Rovaniemi winter quality-check itinerary."""

from __future__ import annotations

from pathlib import Path

from app_modules.itinerary_html import build_itinerary_html
from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.date_resolver import get_day_date_text
from itinerary_generation.exclusion_sections import create_specific_exclusion_sections
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.render_document_builder import build_render_document
from itinerary_generation.transport_domain.routes import get_route_points_for_transport
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from pdf_exporter import export_html_to_pdf
from visual_editor_component.editor_payload_builder import build_visual_editor_payload
from ui.inclusion_pages import paginate_categorized_inclusions


_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "real_inputs" / "finland_winter_quality_check.txt"


def _state():
    rows = normalize_itinerary_rows(parse_itinerary(_FIXTURE.read_text(encoding="utf-8")))
    grouped = group_rows_by_day(rows)
    return rows, grouped


def _render_day(render_document, day: str):
    return next(item for item in render_document.days if item.day == day)


def _day_text(render_document, day: str) -> str:
    render_day = _render_day(render_document, day)
    values = [render_day.title, render_day.intro, render_day.date]
    for block in render_day.blocks:
        values.extend([block.section_title, block.title, block.description])
        values.extend(f"{item.label}: {item.value}" for item in block.meta)
        values.extend(block.lines)
        values.extend(block.includes)
    return "\n".join(value for value in values if value)


def _inclusion_text(rows, grouped) -> str:
    sections = create_categorized_inclusions(rows, grouped)
    return "\n".join(section["title"] + "\n" + "\n".join(section.get("items", [])) for section in sections)


def test_bz1g_tallinn_row_stays_a_self_guided_round_trip_activity() -> None:
    rows, grouped = _state()
    row = next(item for item in rows if item["day"] == "Day 2")
    day_text = _day_text(build_render_document(rows, grouped), "Day 2")

    assert row["type"] == "Activity"
    assert row["effective_type"] == "Activity"
    assert row["activity_product"]["canonical_family"] == "day_excursion_to_tallinn"
    assert "Day Excursion to Tallinn" in day_text
    assert "Helsinki to Tallinn return ferry" in day_text
    assert "at your own pace" in day_text
    assert "Round-trip Helsinki–Tallinn ferry travel" in day_text
    assert "Self-guided time in Tallinn" in day_text
    assert "Ferry Transfer from Helsinki to Tallinn Round Trip" not in day_text


def test_bz1g_activity_contract_preserves_guide_and_snow_condition() -> None:
    rows, grouped = _state()
    render_document = build_render_document(rows, grouped)
    day_3 = _day_text(render_document, "Day 3")
    day_5 = _day_text(render_document, "Day 5")
    inclusions = _inclusion_text(rows, grouped)

    assert "Professional authorised Helsinki guide" in day_3
    assert "Knowledgeable, English-speaking guide" in day_5
    assert "Husky & reindeer sleigh rides if snow conditions allow" in day_5
    assert "Husky & reindeer sleigh rides if snow conditions allow" in inclusions


def test_bz1g_icebreaker_keeps_both_timezones_and_meal_exclusion() -> None:
    rows, grouped = _state()
    day_6 = _day_text(build_render_document(rows, grouped), "Day 6")
    exclusions = create_specific_exclusion_sections(rows)
    exclusion_text = "\n".join("\n".join(items) for items in exclusions.values())

    assert "1:15 PM - 3:45 PM Swedish time / 2:15 PM - 4:45 PM Finnish time" in day_6
    assert "Meals are not included with this experience" in day_6
    assert "Arctic Explorer Icebreaker Cruise Experience in Lapland: Meals" in exclusion_text


def test_bz1g_snowhotel_stay_inclusions_reach_day_and_final_pages() -> None:
    rows, grouped = _state()
    render_document = build_render_document(rows, grouped)
    day_7 = _day_text(render_document, "Day 7")
    inclusions = _inclusion_text(rows, grouped)
    expected = [
        "Guided tour of the SnowHotel",
        "Overnighting instructions and thermal sleeping gear",
        "Access to shared toilets inside the SnowHotel and showers in the sauna area",
        "Wake-up service with a hot drink (optional Northern Lights alert)",
        "Breakfast at the Log Restaurant",
        "Traditional Finnish sauna (shared; bring your swimsuit)",
        "Commemorative diploma for your night beneath snow and ice",
    ]

    assert _render_day(render_document, "Day 7").title == "Arctic Snow Hotel Stay"
    for item in expected:
        assert item in day_7
        assert item in inclusions


def test_bz1g_day_headers_use_the_day_start_date_only() -> None:
    rows, grouped = _state()
    assert get_day_date_text(grouped["Day 4"]) == "13th of December"
    assert _render_day(build_render_document(rows, grouped), "Day 4").date == "13th of December"


def test_bz1g_day_train_direction_service_and_provisional_note_are_canonical() -> None:
    rows, grouped = _state()
    train = next(item for item in rows if item["day"] == "Day 8" and item.get("effective_type") == "Train")
    render_document = build_render_document(rows, grouped)
    day_8 = _day_text(render_document, "Day 8")
    inclusions = _inclusion_text(rows, grouped)

    assert train["title"] == "Train to Helsinki"
    assert get_route_points_for_transport(train) == ("Rovaniemi", "Helsinki")
    assert _render_day(render_document, "Day 8").title == "Train to Helsinki"
    for text in (day_8, inclusions):
        assert "Train from Rovaniemi to Helsinki" in text
        assert "InterCity 24" in text
        assert "9:22 AM - 5:39 PM" in text
        assert "Train timing is provisional and will be confirmed in the final travel voucher" in text
        assert "Train to Rovaniemi" not in text


def test_bz1g_day_8_keeps_all_three_logistics_across_consumers() -> None:
    rows, grouped = _state()
    render_document = build_render_document(rows, grouped)
    editor_payload = build_visual_editor_payload(rows, grouped, {})
    editor_day = next(day for day in editor_payload["days"] if day["day"] == "Day 8")
    pdf_context = build_itinerary_render_context(rows, grouped, {})
    assert pdf_context.trip_glance["End"] == "Helsinki"

    consumer_texts = [
        _day_text(render_document, "Day 8"),
        editor_day["blocks_html"],
        _day_text(pdf_context.render_document, "Day 8"),
    ]
    required = [
        "Transfer from Arctic SnowHotel to Rovaniemi Railway Station",
        "Train from Rovaniemi to Helsinki",
        "Private transfer from Helsinki Railway Station to Helsinki Airport",
    ]
    for consumer_text in consumer_texts:
        for line in required:
            assert line in consumer_text


def test_bz1g_final_inclusions_and_day_blocks_share_source_facts() -> None:
    rows, grouped = _state()
    day_text = "\n".join(_day_text(build_render_document(rows, grouped), day) for day in grouped)
    inclusion_text = _inclusion_text(rows, grouped)

    shared_facts = [
        "Professional authorised Helsinki guide",
        "Husky & reindeer sleigh rides if snow conditions allow",
        "Guided tour of the SnowHotel",
        "InterCity 24",
        "Train timing is provisional and will be confirmed in the final travel voucher",
    ]
    for fact in shared_facts:
        assert fact in day_text
        assert fact in inclusion_text


def test_bz1g_inclusion_pagination_keeps_short_transport_categories_together() -> None:
    rows, grouped = _state()
    pages = paginate_categorized_inclusions(create_categorized_inclusions(rows, grouped))

    assert len(pages) == 2
    assert [section["title"] for section in pages[-1]] == ["Rail journeys", "Other arranged transport"]


def test_bz1g_exact_pdf_has_no_blank_overflow_page_and_keeps_client_facts(tmp_path) -> None:
    import pytest

    fitz = pytest.importorskip("fitz")
    rows, grouped = _state()
    html = build_itinerary_html(rows, grouped, {})
    html_path = tmp_path / "finland-winter.html"
    pdf_path = tmp_path / "finland-winter.pdf"
    html_path.write_text(html, encoding="utf-8")
    export_html_to_pdf(html_path, pdf_path)

    document = fitz.open(pdf_path)
    page_texts = [page.get_text("text") for page in document]
    assert document.page_count == html.count('class="a4-page')
    assert "End\nHelsinki" in page_texts[1]
    assert "End\nHelsinki Railway" not in page_texts[1]
    assert sum("What’s included" in text for text in page_texts) == 2
    assert all(text.strip() for text in page_texts)

    day_8 = next(text for text in page_texts if "DAY 8" in text)
    assert "Train to Helsinki" in day_8
    assert "Transfer from Arctic SnowHotel to Rovaniemi Railway Station" in day_8
    assert "Private transfer from Helsinki Railway Station to Helsinki Airport" in day_8
    assert "Train timing is provisional" in day_8
