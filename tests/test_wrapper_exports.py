from pathlib import Path
from tests.support.static_contracts import read_contract_text


ROOT = Path(__file__).resolve().parents[1]


def test_pdf_exporter_wrapper_uses_explicit_exports():
    source = read_contract_text("pdf_exporter.py")

    assert "import *" not in source
    assert "pdf_exporter_modules.public_api" in source
    assert "__all__" in source

    public_api = read_contract_text(ROOT / "pdf_exporter_modules" / "public_api.py")
    assert "export_html_to_pdf" in public_api
