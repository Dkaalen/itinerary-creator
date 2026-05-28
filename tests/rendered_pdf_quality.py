"""Helpers for rendered-PDF regression checks.

These tests intentionally exercise the final HTML -> ReportLab PDF path,
because many itinerary issues only appear in the exported PDF text rather than
in individual parser/generator objects.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "real_inputs"
EXPECTATIONS_DIR = ROOT / "tests" / "fixtures" / "rendered_pdf_expectations"


def normalize_text(value: str) -> str:
    """Normalize PDF-extracted text for reliable assertions."""
    text = str(value or "")
    text = text.replace("\u00a0", " ")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(value)).strip()


def load_expectation(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lighten_html_for_pdf_quality(html: str) -> str:
    """Keep text/layout path real while avoiding slow image embedding.

    The purpose of these tests is final PDF wording and section placement. Large
    embedded images can make fixture rendering slow and noisy, so the helper
    removes image sources while leaving all text pages, section markup and PDF
    conversion behavior intact.
    """
    html = re.sub(r'--cover-bg-image:\s*url\("data:[^"]+"\);', '--cover-bg-image: none;', html)
    html = re.sub(r'data-cover-background-path="[^"]*"', 'data-cover-background-path=""', html)
    html = re.sub(r'data-image-path="[^"]*"', 'data-image-path=""', html)
    html = re.sub(r'background-image:\s*url\("data:[^"]+"\);', 'background-image: none;', html)
    return html


def render_fixture_pdf_text(fixture_name: str) -> str:
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    import types

    if "streamlit" not in sys.modules:
        streamlit_stub = types.ModuleType("streamlit")

        class _SessionState(dict):
            def __getattr__(self, name):
                return self.get(name)

        streamlit_stub.session_state = _SessionState()
        streamlit_stub.error = lambda *args, **kwargs: None
        streamlit_stub.exception = lambda *args, **kwargs: None
        sys.modules["streamlit"] = streamlit_stub

    from app_modules.itinerary_html import build_itinerary_html
    from generator import group_rows_by_day
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows
    from pdf_exporter import export_html_to_pdf

    fixture_path = FIXTURES_DIR / fixture_name
    if not fixture_path.exists():
        raise AssertionError(f"Fixture not found: {fixture_path}")

    raw = fixture_path.read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    itinerary_html = build_itinerary_html(rows, grouped, output_edits={})
    full_html = _lighten_html_for_pdf_quality("""<!DOCTYPE html>
<html>
<head><meta charset=\"UTF-8\"><title>Fixture Itinerary</title></head>
<body style=\"margin: 0;\">
""" + itinerary_html + """
</body>
</html>""")

    try:
        import fitz
    except Exception as exc:  # pragma: no cover - dependency guard
        raise AssertionError(f"PyMuPDF/fitz is required for rendered PDF quality checks: {exc}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_path = tmp_path / "fixture.html"
        pdf_path = tmp_path / "fixture.pdf"
        html_path.write_text(full_html, encoding="utf-8")
        export_html_to_pdf(html_path, pdf_path)

        document = fitz.open(pdf_path)
        try:
            pages = [page.get_text("text") for page in document]
        finally:
            document.close()

    return normalize_text("\n".join(pages))


def section_between(text: str, start: str, end: str | None = None) -> str:
    compact = normalize_text(text)
    start_index = compact.find(start)
    if start_index == -1:
        raise AssertionError(f"Section start not found in rendered PDF text: {start!r}")
    after_start = compact[start_index:]
    if end:
        end_index = after_start.find(end)
        if end_index != -1:
            return after_start[:end_index]
    return after_start


def assert_expectation(expectation: dict[str, Any], rendered_text: str) -> None:
    text = normalize_text(rendered_text)
    single_line = compact_text(text)

    for expected in expectation.get("must_contain", []):
        if compact_text(expected) not in single_line:
            raise AssertionError(
                f"{expectation.get('name', 'Rendered PDF')} missing required text:\n"
                f"Expected: {expected!r}\n"
                f"PDF text excerpt: {single_line[:2500]!r}"
            )

    for forbidden in expectation.get("must_not_contain", []):
        if compact_text(forbidden) in single_line:
            raise AssertionError(
                f"{expectation.get('name', 'Rendered PDF')} contains forbidden text:\n"
                f"Forbidden: {forbidden!r}"
            )

    for ordered in expectation.get("ordered_must_contain", []):
        cursor = -1
        for expected in ordered:
            needle = compact_text(expected)
            found = single_line.find(needle, cursor + 1)
            if found == -1:
                raise AssertionError(
                    f"{expectation.get('name', 'Rendered PDF')} missing ordered text after position {cursor}: {expected!r}"
                )
            cursor = found

    for section in expectation.get("section_checks", []):
        section_text = compact_text(section_between(text, section["start"], section.get("end")))
        for expected in section.get("must_contain", []):
            if compact_text(expected) not in section_text:
                raise AssertionError(
                    f"{expectation.get('name', 'Rendered PDF')} section {section['start']!r} missing required text: {expected!r}"
                )
        for forbidden in section.get("must_not_contain", []):
            if compact_text(forbidden) in section_text:
                raise AssertionError(
                    f"{expectation.get('name', 'Rendered PDF')} section {section['start']!r} contains forbidden text: {forbidden!r}"
                )
        for ordered in section.get("ordered_must_contain", []):
            cursor = -1
            for expected in ordered:
                needle = compact_text(expected)
                found = section_text.find(needle, cursor + 1)
                if found == -1:
                    raise AssertionError(
                        f"{expectation.get('name', 'Rendered PDF')} section {section['start']!r} missing ordered text after position {cursor}: {expected!r}"
                    )
                cursor = found


def expectation_files() -> list[Path]:
    return sorted(EXPECTATIONS_DIR.glob("*.json"))
