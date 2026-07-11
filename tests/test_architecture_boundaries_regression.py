from pathlib import Path
from tests.support.static_contracts import read_contract_text

from shared.source_rows import edit_row_id, rows_by_source_id, source_row_id, source_text
from shared.text import clean_space


ROOT = Path(__file__).resolve().parents[1]


def test_source_row_helpers_live_in_neutral_shared_package() -> None:
    row = {"line_number": 12, "title": "  Northern   Lights  ", "details": " Aurora\xa0hunt "}

    generated_id = source_row_id(row, 3)
    assert generated_id.startswith("generated-row-")
    assert generated_id == source_row_id(row, 99)
    assert edit_row_id(row, 3) == "line_12"
    assert source_text(row, fields=("title", "details"), separator=" | ") == "Northern   Lights | Aurora\xa0hunt"
    lookup = rows_by_source_id([{"row_id": "r1"}, {}])
    assert lookup["r1"] == {"row_id": "r1"}
    assert list(lookup)[1].startswith("generated-row-")
    assert clean_space("A\xa0  B\r\nC") == "A B C"


def test_generation_source_identity_is_compatibility_only() -> None:
    source = read_contract_text(ROOT / "itinerary_generation" / "source_identity.py")

    assert "from shared.source_rows import" in source
    assert "New code should import from :mod:`shared.source_rows`" in source


def test_core_render_modules_import_neutral_source_row_helpers() -> None:
    checked = [
        ROOT / "itinerary_generation" / "canonical_helpers.py",
        ROOT / "itinerary_generation" / "day_render_blocks.py",
        ROOT / "itinerary_generation" / "qa_report.py",
        ROOT / "itinerary_generation" / "render_document_builder.py",
        ROOT / "itinerary_generation" / "structured_builder.py",
        ROOT / "itinerary_generation" / "structured_inclusions.py",
    ]

    for path in checked:
        text = path.read_text(encoding="utf-8")
        assert "from shared.source_rows import" in text
        assert "from itinerary_generation.source_identity import" not in text
