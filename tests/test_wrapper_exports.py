from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pdf_exporter_wrapper_uses_explicit_exports():
    source = (ROOT / "pdf_exporter.py").read_text(encoding="utf-8")

    assert "import *" not in source
    assert "__all__" in source
    assert "export_html_to_pdf" in source
