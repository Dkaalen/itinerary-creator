import ast
from pathlib import Path

from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from itinerary_generation.render_document_builder import build_render_document
from itinerary_generation.render_model import RenderDocument
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.canonical_model import CanonicalBlock
from ui.day_page_sections import render_day_pages

ROOT = Path(__file__).resolve().parents[1]


def _rows(raw: str):
    return normalize_itinerary_rows(parse_itinerary(raw))


def test_canonical_block_no_longer_stores_generated_html_bridge():
    assert "html" not in CanonicalBlock.__dataclass_fields__


def test_render_document_preserves_structured_day_source_identity():
    rows = _rows(
        """
        Day 1	Activity		01/01/2026		09:00 AM	2 hours			Tromsø	Northern Lights Photography Tour
        Day 1	Hotel	1	01/01/2026	02/01/2026				Tromsø	Clarion Hotel The Edge, 1xNight, Incl Breakfast
        """
    )
    grouped = group_rows_by_day(rows)
    document = build_itinerary_document(rows, grouped)
    render_document = build_render_document(rows, grouped)

    assert isinstance(render_document, RenderDocument)
    assert [day.day for day in render_document.days] == [day.day for day in document.days]
    assert render_document.days[0].source_row_ids == list(document.days[0].source_row_ids)
    assert all(not hasattr(block, "html") for day in render_document.days for block in day.blocks)


def test_render_day_pages_uses_supplied_render_document_without_rebuilding_days(monkeypatch):
    rows = _rows(
        """
        Day 1	Activity		01/01/2026		09:00 AM	2 hours			Tromsø	Northern Lights Photography Tour
        """
    )
    grouped = group_rows_by_day(rows)
    render_document = build_render_document(rows, grouped)

    def fail_if_called(*args, **kwargs):  # pragma: no cover - used as a guard
        raise AssertionError("render_day_pages should consume the supplied RenderDocument")

    monkeypatch.setattr("ui.day_page_sections.build_render_day", fail_if_called)
    html = render_day_pages(grouped, render_document=render_document)

    assert "Northern Lights" in html
    assert "day-section" in html


def test_itinerary_html_builds_render_document_from_structured_document():
    source = (ROOT / "app_modules" / "itinerary_html.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "build_itinerary_document" in call_names
    assert "build_render_document_from_document" in call_names
    assert "render_day_pages" in call_names


def test_render_model_has_no_upstream_canonical_dependency():
    source = (ROOT / "itinerary_generation" / "render_model.py").read_text(encoding="utf-8")
    assert "canonical_model" not in source
    assert "render_block_from_canonical" not in source


def test_canonical_to_render_adapter_is_the_only_canonical_bridge():
    source = (ROOT / "itinerary_generation" / "canonical_render_adapter.py").read_text(encoding="utf-8")
    assert "from itinerary_generation.canonical_model" in source
    assert "from itinerary_generation.render_model" in source
