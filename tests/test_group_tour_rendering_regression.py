"""Patch IH4 gates for canonical Iceland group-tour rendering and parity."""

from __future__ import annotations

from functools import lru_cache
from html import unescape
from pathlib import Path
import re

import pytest

from app_modules.itinerary_html import build_itinerary_html
from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.group_tour_domain import group_tour_package_from_row
from itinerary_generation.group_tour_rendering import group_tour_day_title
from itinerary_generation.quality_gate import evaluate_client_output_quality, render_document_text
from itinerary_generation.reference_corpus import iceland_reference_payload
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from pdf_exporter_modules.typed_exporter import export_render_document_to_pdf
from visual_editor_component.editor_payload_builder import build_visual_editor_payload


GROUP_SHEETS = tuple(
    f"{days}D {code}"
    for code in ("GTS", "GTW")
    for days in (5, 6, 7, 8, 10)
)


def _sheet(name: str) -> dict:
    return next(item for item in iceland_reference_payload()["sheets"] if item["sheet_name"] == name)


@lru_cache(maxsize=None)
def _state(name: str):
    sheet = _sheet(name)
    rows = normalize_itinerary_rows(
        sheet["rows"],
        source_name=sheet["sheet_name"],
        group_tour_season=sheet["season"],
    )
    grouped = group_rows_by_day(rows)
    package = next(
        package
        for row in rows
        if (package := group_tour_package_from_row(row)) is not None
    )
    context = build_itinerary_render_context(rows, grouped, {})
    return rows, grouped, package, context


@lru_cache(maxsize=None)
def _legacy_state(name: str):
    source = (Path(__file__).parent / "fixtures" / "real_inputs" / name).read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(source))
    grouped = group_rows_by_day(rows)
    package = next(
        package
        for row in rows
        if (package := group_tour_package_from_row(row)) is not None
    )
    context = build_itinerary_render_context(rows, grouped, {})
    return rows, grouped, package, context


def _group_blocks(context):
    return [
        (day, block)
        for day in context.render_document.days
        for block in day.blocks
        if block.kind == "group_tour_day"
    ]


def _section_items(context, title: str):
    section = next(item for item in context.structured_document.inclusions if item.title == title)
    return list(section.items)


def test_all_ten_sheets_render_one_canonical_block_per_package_day() -> None:
    for name in GROUP_SHEETS:
        rows, _grouped, package, context = _state(name)
        blocks = _group_blocks(context)

        assert len(blocks) == package.duration_days
        assert [day.day for day, _block in blocks] == [
            f"Day {segment.itinerary_day_number}" for segment in package.day_segments
        ]
        assert [block.section_title for _day, block in blocks] == [
            f"Group Tour · Day {index} of {package.duration_days}"
            for index in range(1, package.duration_days + 1)
        ]
        assert not any(
            block.row_id == row.get("row_id")
            for day in context.render_document.days
            for block in day.blocks
            for row in rows
            if row.get("group_tour_role") == "package_master"
        )


def test_day_header_block_and_editor_share_the_same_contract() -> None:
    for name in GROUP_SHEETS:
        rows, grouped, package, context = _state(name)
        editor = build_visual_editor_payload(rows, grouped, {})
        editor_by_day = {day["day"]: day for day in editor["days"]}
        rendered_by_day = {day.day: day for day in context.render_document.days}

        for segment in package.day_segments:
            day_id = f"Day {segment.itinerary_day_number}"
            expected = group_tour_day_title(grouped[day_id])
            render_day = rendered_by_day[day_id]
            blocks = [block for block in render_day.blocks if block.kind == "group_tour_day"]

            assert render_day.title == expected
            assert len(blocks) == 1
            assert blocks[0].title == expected
            assert editor_by_day[day_id]["title"] == expected
            assert expected in unescape(editor_by_day[day_id]["blocks_html"])
            assert f"Group Tour · Day {segment.package_day_number} of {package.duration_days}" in editor_by_day[day_id]["blocks_html"]


def test_final_inclusions_list_each_package_once_not_each_package_day() -> None:
    for name in GROUP_SHEETS:
        _rows, _grouped, package, context = _state(name)
        activities = _section_items(context, "Activities & experiences")
        package_items = [item for item in activities if item.category == "group_tour"]

        assert len(package_items) == 1
        assert package_items[0].label == package.title
        assert any(
            f"Guided {package.duration_days}-day Iceland programme" in line
            and f"{package.season} group tour" in line
            for line in package_items[0].detail_lines
        )
        assert any("detailed daily programme" in line.lower() for line in package_items[0].detail_lines)
        assert not any(
            item.label == segment.title
            for item in activities
            for segment in package.day_segments
        )


def test_package_accommodation_does_not_replace_pre_or_post_tour_hotels() -> None:
    rows, _grouped, package, context = _state("6D GTW")
    accommodation_items = _section_items(context, "Accommodation")
    package_item = next(
        item
        for item in _section_items(context, "Activities & experiences")
        if item.category == "group_tour"
    )

    independent_hotel_rows = [
        row
        for row in rows
        if (row.get("effective_type") or row.get("type")) == "Hotel"
        and row.get("group_tour_role") != "commercial_item"
    ]
    assert len(independent_hotel_rows) == 2
    assert len(accommodation_items) == 2
    assert package.accommodation_policy.included is True
    assert package.accommodation_policy.nights == package.duration_days - 1
    assert any(f"{package.accommodation_policy.nights} included nights" in line for line in package_item.detail_lines)
    assert any("Properties may vary according to availability" in line for line in package_item.detail_lines)


def test_legacy_package_accommodation_is_not_recreated_as_hotel_products() -> None:
    rows, grouped, package, context = _legacy_state("iceland_group_tour_winter.txt")
    accommodation_items = _section_items(context, "Accommodation")
    activity_items = _section_items(context, "Activities & experiences")
    group_blocks = _group_blocks(context)

    assert not any(
        row.get("is_group_tour_accommodation")
        for day_rows in grouped.values()
        for row in day_rows
    )
    assert [item.label for item in accommodation_items] == [
        "3-star Fosshotel Raudara, Reykjavík",
        "3-star Center Hotels Skjaldbreið, Reykjavík",
    ]
    assert len([item for item in activity_items if item.category == "group_tour"]) == 1
    assert not any(
        item.label == segment.title
        for item in activity_items
        for segment in package.day_segments
    )
    assert [block.section_title for _day, block in group_blocks] == [
        f"Group Tour · Day {index} of {package.duration_days}"
        for index in range(1, package.duration_days + 1)
    ]
    overnight_sections = [
        section.items[0]
        for _day, block in group_blocks
        for section in block.extra_sections
        if section.title == "Included Overnight"
    ]
    assert overnight_sections == [
        "Breakfast included at Reykjavík hotel.",
        "Breakfast included at West Iceland guesthouse.",
        "Breakfast included at Countryside guesthouse.",
        "Breakfast included at South Coast guesthouse.",
    ]
    assert all(row.get("group_tour_role") != "day_segment" or row.get("type") == "Activity" for row in rows)


def test_optional_and_commercial_items_never_become_package_inclusions() -> None:
    _rows, _grouped, package, context = _state("10D GTS")
    package_item = next(
        item
        for item in _section_items(context, "Activities & experiences")
        if item.category == "group_tour"
    )
    package_text = "\n".join((package_item.label, *package_item.detail_lines))
    optional_titles = {
        item.title
        for item in package.commercial_items
        if item.optional and not item.selected
    }

    assert optional_titles
    assert all(title not in package_text for title in optional_titles)
    assert "Single Supplement Fee" not in package_text
    assert "Extra Hotel Night" not in package_text
    assert any("Horseback Riding" in item["title"] for item in context.optional_addons)
    assert any("VÖK Baths" in item["title"] for item in context.optional_addons)
    assert not any("Single Supplement" in item["title"] for item in context.optional_addons)


def test_preview_contains_one_package_and_ordered_daily_segments() -> None:
    rows, grouped, package, _context = _state("8D GTW")
    html = unescape(build_itinerary_html(rows, grouped, {}))

    assert html.count(package.title) == 1
    offsets = [html.index(f"Group Tour · Day {index} of {package.duration_days}") for index in range(1, package.duration_days + 1)]
    assert offsets == sorted(offsets)
    for segment in package.day_segments:
        assert group_tour_day_title(grouped[f"Day {segment.itinerary_day_number}"]) in html
    assert "Single Supplement Fee" in html  # Correctly shown as not included/commercial, not hidden.


@pytest.mark.parametrize("name", ["5D GTS", "5D GTW"])
def test_typed_pdf_uses_the_same_summer_and_winter_contract(name: str, tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    _rows, _grouped, package, context = _state(name)
    pdf_path = tmp_path / f"{name.replace(' ', '-').lower()}.pdf"

    export_render_document_to_pdf(context.render_document, pdf_path)

    document = fitz.open(pdf_path)
    try:
        text = "\n".join(page.get_text("text") for page in document)
        normalized_text = re.sub(r"\s+", " ", text)
        assert package.title in text
        assert f"Guided {package.duration_days}-day Iceland programme" in text
        assert f"{package.season} group tour" in text
        for index, segment in enumerate(package.day_segments, start=1):
            expected = group_tour_day_title(context.grouped_days[f"Day {segment.itinerary_day_number}"])
            assert re.sub(r"\s+", " ", expected) in normalized_text
            assert f"Group Tour · Day {index} of {package.duration_days}" in text
        assert document.page_count >= len(context.render_document.days) + 3
    finally:
        document.close()


def test_route_summary_and_season_are_package_owned() -> None:
    _summer_rows, _summer_grouped, summer, summer_context = _state("10D GTS")
    _winter_rows, _winter_grouped, winter, winter_context = _state("10D GTW")

    assert summer.season == "summer"
    assert winter.season == "winter"
    assert "guided summer Iceland group tour" in summer_context.trip_subtitle
    assert "guided winter Iceland group tour" in winter_context.trip_subtitle
    assert summer_context.trip_glance["Travel Style"] == "Guided group tour"
    assert winter_context.trip_glance["Travel Style"] == "Guided group tour"
    for context in (summer_context, winter_context):
        assert "South Coast" in context.destinations_line
        assert "Jökulsárlón" in context.destinations_line
        assert "TBA" not in context.destinations_line


def test_season_conflict_remains_visible_without_cross_contaminating_rendering() -> None:
    _rows, _grouped, package, context = _state("7D GTS")

    assert package.season == "summer"
    assert "Winter Minibus Tour" in package.title
    assert "group_tour_season_source_conflict" in package.warnings
    assert "guided summer Iceland group tour" in context.trip_subtitle
    assert "guided winter Iceland group tour" not in context.trip_subtitle


def test_client_output_quality_accepts_all_ten_group_tour_sheets() -> None:
    for name in GROUP_SHEETS:
        _rows, _grouped, _package, context = _state(name)
        report = evaluate_client_output_quality(context.render_document)
        text = render_document_text(context.render_document)

        assert not report.blocking_issues, (name, report.blocking_issues)
        assert "Group Tour · Day" in text
        assert "Single Supplement Fee" not in "\n".join(
            item.label + "\n" + "\n".join(item.detail_lines)
            for item in _section_items(context, "Activities & experiences")
        )
