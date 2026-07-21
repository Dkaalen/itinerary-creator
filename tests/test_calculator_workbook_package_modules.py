from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from calculator.workbook_export_plan import ExportCell
from calculator.workbook_package_cell_changes import generate_cell_changes
from calculator.workbook_recalculation_xml import patch_workbook_calculation_properties
from calculator.workbook_worksheet_xml import patch_worksheet_xml
from calculator.workbook_zip_package import clone_xlsx_package


def test_cell_change_generation_is_validated_and_duplicate_free() -> None:
    changes = generate_cell_changes(
        (
            ExportCell("A1", "Text", "text"),
            ExportCell("B2", 12.5, "number"),
        )
    )

    assert changes["A1"].value == "Text"
    assert changes["A1"].kind == "text"
    assert changes["B2"].value == 12.5

    with pytest.raises(ValueError, match="Duplicate export cell reference: A1"):
        generate_cell_changes(
            (
                ExportCell("A1", 1, "number"),
                ExportCell("A1", 2, "number"),
            )
        )
    with pytest.raises(ValueError, match="Invalid export cell reference"):
        generate_cell_changes((ExportCell("a1", 1, "number"),))


def test_worksheet_xml_mutation_updates_and_inserts_cells_in_order() -> None:
    xml = (
        '<worksheet><dimension ref="A1:C3"/><sheetData>'
        '<row r="1"><c r="A1"><v>1</v></c><c r="C1"><v>3</v></c></row>'
        '<row r="3"><c r="A3"><v>7</v></c></row>'
        '</sheetData></worksheet>'
    )
    changes = generate_cell_changes(
        (
            ExportCell("A1", "Changed", "text"),
            ExportCell("B1", 2, "number"),
            ExportCell("A2", "Inserted", "text"),
        )
    )

    patched = patch_worksheet_xml(xml, changes, dimension_ref="A1:C3")

    assert '<c r="A1" t="inlineStr"><is><t xml:space="preserve">Changed</t></is></c>' in patched
    assert patched.index('r="A1"') < patched.index('r="B1"') < patched.index('r="C1"')
    assert patched.index('<row r="1">') < patched.index('<row r="2">') < patched.index('<row r="3">')
    assert '<c r="A2" t="inlineStr"><is><t xml:space="preserve">Inserted</t></is></c>' in patched


def test_recalculation_metadata_is_updated_without_replacing_other_attributes() -> None:
    xml = '<workbook><calcPr calcId="191029" calcMode="manual"/></workbook>'

    patched = patch_workbook_calculation_properties(
        xml,
        {
            "calcMode": "auto",
            "fullCalcOnLoad": True,
            "forceFullCalc": True,
        },
    )

    assert 'calcId="191029"' in patched
    assert 'calcMode="auto"' in patched
    assert 'fullCalcOnLoad="1"' in patched
    assert 'forceFullCalc="1"' in patched


def test_zip_package_clone_preserves_order_metadata_and_unreplaced_bytes() -> None:
    source_buffer = BytesIO()
    first_info = ZipInfo("first.xml", date_time=(2020, 1, 2, 3, 4, 6))
    first_info.compress_type = ZIP_DEFLATED
    first_info.comment = b"first"
    second_info = ZipInfo("second.bin", date_time=(2021, 2, 3, 4, 5, 6))
    second_info.compress_type = ZIP_DEFLATED
    second_info.external_attr = 0o644 << 16
    with ZipFile(source_buffer, "w") as archive:
        archive.writestr(first_info, b"old")
        archive.writestr(second_info, b"unchanged")

    with ZipFile(BytesIO(source_buffer.getvalue()), "r") as source:
        content = clone_xlsx_package(source, {"first.xml": b"new"})
        source_infos = source.infolist()

    with ZipFile(BytesIO(content), "r") as cloned:
        cloned_infos = cloned.infolist()
        assert cloned.namelist() == ["first.xml", "second.bin"]
        assert cloned.read("first.xml") == b"new"
        assert cloned.read("second.bin") == b"unchanged"
        assert cloned_infos[0].date_time == source_infos[0].date_time
        assert cloned_infos[0].comment == source_infos[0].comment
        assert cloned_infos[1].external_attr == source_infos[1].external_attr
