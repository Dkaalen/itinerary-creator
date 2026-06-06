from pathlib import Path
import sys
import types

streamlit_stub = types.SimpleNamespace(
    session_state={},
    error=lambda *args, **kwargs: None,
    exception=lambda *args, **kwargs: None,
    expander=lambda *args, **kwargs: types.SimpleNamespace(__enter__=lambda self: self, __exit__=lambda self, exc_type, exc, tb: False),
)
sys.modules.setdefault("streamlit", streamlit_stub)

from app_modules.itinerary_render_context import build_itinerary_render_context
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.render_model import RenderDocument, RenderFinalPage, RenderFinalSection
from pdf_exporter import export_render_document_to_pdf, render_document_requires_html_fallback
from ui import export_files


def _sample_rows():
    return [
        {
            "row_id": "row-1",
            "type": "Activity",
            "effective_type": "Activity",
            "day": "Day 1",
            "city": "Oslo",
            "title": "Guided Oslo Walk",
            "description": "Explore the harbour and city centre with a local guide.",
            "client_description": "Explore the harbour and city centre with a local guide.",
            "commercial_status": "included",
        },
        {
            "row_id": "row-2",
            "type": "Transfer",
            "effective_type": "Transfer",
            "day": "Day 1",
            "city": "Oslo",
            "title": "Private transfer from Oslo Airport to your hotel",
            "commercial_status": "included",
        },
    ]


def _context(output_edits=None):
    rows = _sample_rows()
    grouped = group_rows_by_day(rows)
    return build_itinerary_render_context(rows, grouped, output_edits or {})


def test_render_context_attaches_pdf_contract_to_render_document():
    context = _context({"important_travel_notes_text": "Bring passport"})

    assert isinstance(context.render_document, RenderDocument)
    assert context.render_document.cover is not None
    assert context.render_document.cover.title
    assert context.render_document.summary is not None
    assert context.render_document.summary.trip_glance
    section_ids = [section.section_id for section in context.render_document.final_sections]
    assert "whats_included" in section_ids
    assert "whats_not_included" in section_ids
    assert "important_travel_notes" in section_ids


def test_direct_pdf_exporter_writes_from_render_document_without_html(tmp_path):
    context = _context({"important_travel_notes_text": "Bring passport"})
    pdf_path = tmp_path / "typed.pdf"

    export_render_document_to_pdf(context.render_document, pdf_path, color_data=context.colors)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 3_000


def test_save_pdf_file_prefers_typed_renderer_when_model_owns_content(monkeypatch, tmp_path):
    context = _context({"important_travel_notes_text": "Bring passport"})
    html_path = tmp_path / "preview.html"
    html_path.write_text("<html><body>legacy preview</body></html>", encoding="utf-8")
    calls = []

    def fake_typed(render_document, pdf_path, **kwargs):
        calls.append(("typed", isinstance(render_document, RenderDocument), kwargs))
        Path(pdf_path).write_bytes(b"typed pdf")

    def fake_html(html_path_arg, pdf_path):
        calls.append(("html", str(html_path_arg), {}))
        Path(pdf_path).write_bytes(b"html pdf")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(export_files, "export_render_document_to_pdf", fake_typed)
    monkeypatch.setattr(export_files, "export_html_to_pdf", fake_html)

    output_path = export_files.save_pdf_file(
        html_path,
        render_document=context.render_document,
        color_data=context.colors,
        output_edits={"important_travel_notes_text": "Bring passport"},
    )

    assert output_path == Path("outputs/itinerary_preview.pdf")
    assert calls and calls[0][0] == "typed"
    assert calls[0][1] is True


def test_save_pdf_file_falls_back_when_visual_editor_html_owns_content(monkeypatch, tmp_path):
    context = _context()
    context.render_document.final_sections.append(
        RenderFinalSection(
            "whats_included",
            "What’s included",
            pages=[RenderFinalPage(content_html="<ul><li>Edited inclusion</li></ul>")],
        )
    )
    html_path = tmp_path / "preview.html"
    html_path.write_text("<html><body>edited preview</body></html>", encoding="utf-8")
    calls = []

    def fake_typed(render_document, pdf_path, **kwargs):
        calls.append("typed")
        Path(pdf_path).write_bytes(b"typed pdf")

    def fake_html(html_path_arg, pdf_path):
        calls.append("html")
        Path(pdf_path).write_bytes(b"html pdf")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(export_files, "export_render_document_to_pdf", fake_typed)
    monkeypatch.setattr(export_files, "export_html_to_pdf", fake_html)

    output_path = export_files.save_pdf_file(html_path, render_document=context.render_document, output_edits={})

    assert output_path == Path("outputs/itinerary_preview.pdf")
    assert calls == ["html"]
    assert render_document_requires_html_fallback(context.render_document, {}) is True
