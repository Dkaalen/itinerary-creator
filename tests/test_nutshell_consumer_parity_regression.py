"""Patch BZ1C gates for Norway in a Nutshell consumer parity."""

from __future__ import annotations

from pathlib import Path

from tests.support.static_contracts import read_contract_text
from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.nutshell_domain import nutshell_journey_from_row
from itinerary_generation.render_document_builder import build_render_document
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from generator import group_rows_by_day
from ui.day_blocks import build_day_blocks
from visual_editor_component.editor_payload_builder import build_visual_editor_payload


_REAL_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "real_inputs"
    / "scandinavia_cruise_premium_working.txt"
)
_CANONICAL_TITLE = "Norway in a Nutshell from Bergen to Oslo"
_OBSOLETE_TITLE = "Scenic Rail & Fjord Journey from Bergen to Oslo"
_RAW_PRODUCT_TITLE = "Bergen to Oslo: Day Tour incl. the Flåm Train"


def _real_state() -> tuple[list[dict], dict[str, list[dict]], dict]:
    rows = normalize_itinerary_rows(parse_itinerary(_REAL_FIXTURE.read_text(encoding="utf-8")))
    grouped = group_rows_by_day(rows)
    nutshell_row = next(
        row
        for row in rows
        if (row.get("activity_product") or {}).get("canonical_family") == "norway_in_a_nutshell"
    )
    return rows, grouped, nutshell_row


def _day_lines(render_document, day: str) -> list[str]:
    render_day = next(item for item in render_document.days if item.day == day)
    lines: list[str] = []
    for block in render_day.blocks:
        if block.title:
            lines.append(block.title)
        lines.extend(block.lines)
        for section in block.extra_sections:
            lines.extend(section.items)
    return lines


def test_preview_editor_and_pdf_contract_share_canonical_product_title() -> None:
    rows, grouped, _ = _real_state()

    preview_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 16"]) if block)
    render_document = build_render_document(rows, grouped)
    editor_payload = build_visual_editor_payload(rows, grouped, {})
    editor_day = next(day for day in editor_payload["days"] if day["day"] == "Day 16")
    pdf_context = build_itinerary_render_context(rows, grouped, {})

    consumer_texts = [
        preview_html,
        "\n".join(_day_lines(render_document, "Day 16")),
        editor_day["blocks_html"],
        "\n".join(_day_lines(pdf_context.render_document, "Day 16")),
    ]
    for text in consumer_texts:
        assert _CANONICAL_TITLE in text
        assert _OBSOLETE_TITLE not in text
        assert _RAW_PRODUCT_TITLE not in text


def test_structured_inclusions_use_contract_title_source_identity_and_services() -> None:
    rows, grouped, nutshell_row = _real_state()
    document = build_itinerary_document(rows, grouped)
    scenic_section = next(section for section in document.inclusions if section.title == "Scenic rail & fjord journeys")
    nutshell_item = next(item for item in scenic_section.items if item.label == _CANONICAL_TITLE)

    assert nutshell_item.source_row_ids == (nutshell_row["row_id"],)
    detail_text = "\n".join(nutshell_item.detail_lines)
    assert "E-Tickets for Fjord Cruise: Gudvangen to Flåm" in detail_text
    assert "E-Tickets for Flåm railway: Flåm to Myrdal" in detail_text
    assert _OBSOLETE_TITLE not in detail_text
    assert _RAW_PRODUCT_TITLE not in detail_text


def test_discontinuous_supplier_legs_are_not_reordered_or_rendered_as_route_highlights() -> None:
    rows, grouped, nutshell_row = _real_state()
    journey = nutshell_journey_from_row(nutshell_row)
    preview_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 16"]) if block)

    assert journey is not None
    assert "route_leg_discontinuity" in journey.warnings
    assert journey.route_points == ("Bergen", "Oslo")
    assert "Route highlights:" not in preview_html
    assert "Bergen, Oslo, Voss" not in preview_html
    assert "E-tickets for bus: Voss to Gudvangen" in preview_html


def test_normalized_timetable_contract_drives_route_highlights_without_reparsing() -> None:
    raw = '''Day 1\tTransfer\t02/01/2027\t\t\t\t\t\t\t\t\tOslo\t"Norway in a Nutshell | Bergen to Oslo | 08:30 - 22:30 | Including luggage porter service
08:29 Bergen
09:41 Voss
10:10 Voss
11:10 Gudvangen
12:00 Gudvangen
14:00 Flåm
16:50 Flåm
17:30 Myrdal
17:40 Myrdal
22:27 Oslo"'''
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    journey = nutshell_journey_from_row(rows[0])
    day_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 1"]) if block)

    assert journey is not None
    assert journey.route_points == ("Bergen", "Voss", "Gudvangen", "Flåm", "Myrdal", "Oslo")
    assert journey.warnings == ()
    assert _CANONICAL_TITLE in day_html
    assert "Bergen → Voss → Gudvangen → Flåm → Myrdal → Oslo" in day_html


def test_generic_travel_renderer_no_longer_owns_nutshell_product_copy() -> None:
    render_source = read_contract_text("itinerary_generation/transport_domain/render.py")

    assert "Scenic Rail & Fjord Journey" not in render_source
    assert "extract_norway_nutshell_route_legs" not in render_source
    assert "extract_norway_nutshell_route_points" not in render_source
    assert "resolve_nutshell_journey" in render_source
