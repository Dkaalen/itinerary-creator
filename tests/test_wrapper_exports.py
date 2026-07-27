from pathlib import Path

from tests.support.static_contracts import read_contract_text


ROOT = Path(__file__).resolve().parents[1]


def test_pdf_exporter_is_the_explicit_supported_api() -> None:
    source = read_contract_text("pdf_exporter.py")

    assert "import *" not in source
    assert "Supported public API" in source
    assert "def create_pdf(" in source
    assert "__all__" in source
    assert "pdf_exporter_modules.public_api" not in source
    assert not (ROOT / "pdf_exporter_modules" / "public_api.py").exists()
