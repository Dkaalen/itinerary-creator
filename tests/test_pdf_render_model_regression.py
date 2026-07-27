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
from pdf_exporter import PdfExportResult, export_render_document_to_pdf, render_document_requires_html_fallback
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


def _created_result(pdf_path: str | Path, renderer: str) -> PdfExportResult:
    path = Path(pdf_path)
    path.write_bytes(f"{renderer} pdf".encode("utf-8"))
    return PdfExportResult(status="created", path=path, renderer=renderer)


def test_save_pdf_file_delegates_prepared_document_to_supported_api(monkeypatch, tmp_path):
    context = _context({"important_travel_notes_text": "Bring passport"})
    html_path = tmp_path / "preview.html"
    html_path.write_text("<html><body>legacy preview</body></html>", encoding="utf-8")
    calls = []

    def fake_create_pdf(html_path_arg, pdf_path, **kwargs):
        calls.append((Path(html_path_arg), Path(pdf_path), kwargs))
        return _created_result(pdf_path, "typed")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(export_files, "create_pdf", fake_create_pdf)

    output_path = export_files.save_pdf_file(
        html_path,
        render_document=context.render_document,
        color_data=context.colors,
        output_edits={"important_travel_notes_text": "Bring passport"},
    )

    assert output_path == Path("outputs/itinerary_preview.pdf")
    assert len(calls) == 1
    assert calls[0][0] == html_path
    assert calls[0][2]["render_document"] is context.render_document
    assert calls[0][2]["color_data"] == context.colors


def test_save_pdf_file_keeps_supported_final_html_on_supported_api(monkeypatch, tmp_path):
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

    def fake_create_pdf(html_path_arg, pdf_path, **kwargs):
        calls.append(kwargs["render_document"])
        return _created_result(pdf_path, "typed")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(export_files, "create_pdf", fake_create_pdf)

    output_path = export_files.save_pdf_file(
        html_path, render_document=context.render_document, output_edits={}
    )

    assert output_path == Path("outputs/itinerary_preview.pdf")
    assert calls == [context.render_document]
    assert render_document_requires_html_fallback(context.render_document, {}) is False


def test_save_pdf_file_delegates_unsupported_editor_html_for_fallback(monkeypatch, tmp_path):
    context = _context()
    context.render_document.final_sections.append(
        RenderFinalSection(
            "whats_included",
            "What’s included",
            pages=[RenderFinalPage(content_html="<table><tr><td>Unsupported layout</td></tr></table>")],
        )
    )
    html_path = tmp_path / "preview.html"
    html_path.write_text("<html><body>edited preview</body></html>", encoding="utf-8")
    calls = []

    def fake_create_pdf(html_path_arg, pdf_path, **kwargs):
        calls.append(kwargs["render_document"])
        return _created_result(pdf_path, "html")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(export_files, "create_pdf", fake_create_pdf)

    output_path = export_files.save_pdf_file(
        html_path, render_document=context.render_document, output_edits={}
    )

    assert output_path == Path("outputs/itinerary_preview.pdf")
    assert calls == [context.render_document]
    assert render_document_requires_html_fallback(context.render_document, {}) is True


def test_save_pdf_file_still_falls_back_when_supported_day_html_is_not_in_render_document():
    assert render_document_requires_html_fallback(
        RenderDocument(),
        {"days": {"Day 1": {"blocks_html": "<div>Edited day body</div>"}}},
    ) is True


def test_save_pdf_file_still_falls_back_for_unsupported_day_body_html():
    assert render_document_requires_html_fallback(
        RenderDocument(),
        {"days": {"Day 1": {"blocks_html": "<table><tr><td>Unsupported day layout</td></tr></table>"}}},
    ) is True


def test_render_context_moves_supported_manual_day_html_into_typed_document():
    context = _context({"days": {"Day 1": {"blocks_html": "<div class=\"content-block\"><div class=\"body-text\">Typed edited day</div></div>"}}})

    assert context.render_document.days[0].blocks[0].kind == "manual_day_html"
    assert "Typed edited day" in context.render_document.days[0].blocks[0].content_html
    assert render_document_requires_html_fallback(context.render_document, context.output_edits) is False
