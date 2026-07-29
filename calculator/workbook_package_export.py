"""Apply a canonical calculator export plan to the reference XLSX package.

The workbook is an immutable visual/structural template. This public renderer
owns orchestration and bounded caching only. Package cell changes, worksheet
XML mutation, recalculation metadata, and ZIP cloning have separate owners.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from calculator.template_structure import default_template_path
from calculator.workbook_export_plan import WorkbookExportPlan
from calculator.workbook_date_metadata import patch_date_metadata_xml
from calculator.workbook_package_cell_changes import generate_cell_changes
from calculator.workbook_package_integrity import remove_calc_chain_content_type, remove_calc_chain_relationship
from calculator.workbook_recalculation_xml import patch_workbook_calculation_properties
from calculator.workbook_provenance import patch_custom_properties_xml
from calculator.workbook_worksheet_xml import patch_worksheet_xml
from calculator.workbook_zip_package import clone_xlsx_package

_CURR_SHEET_PART = "xl/worksheets/sheet1.xml"
_KALK_SHEET_PART = "xl/worksheets/sheet2.xml"
_WORKBOOK_PART = "xl/workbook.xml"
_WORKBOOK_RELS_PART = "xl/_rels/workbook.xml.rels"
_CONTENT_TYPES_PART = "[Content_Types].xml"
_CUSTOM_PROPERTIES_PART = "docProps/custom.xml"
_CALC_CHAIN_PART = "xl/calcChain.xml"
_BASE_CHANGED_PARTS = (_CURR_SHEET_PART, _KALK_SHEET_PART, _WORKBOOK_PART, _WORKBOOK_RELS_PART, _CONTENT_TYPES_PART)
_DELETED_PARTS = (_CALC_CHAIN_PART,)
_EXPORT_CACHE_LIMIT = 2
_EXPORT_CACHE: OrderedDict[tuple[str, str, int, int], "PackageExportResult"] = OrderedDict()


@dataclass(frozen=True)
class PackageExportResult:
    """Exact-reference XLSX bytes and the package parts intentionally changed."""

    content: bytes
    changed_parts: tuple[str, ...]
    deleted_parts: tuple[str, ...] = ()


def export_reference_workbook_package(
    plan: WorkbookExportPlan,
    template_path: str | Path | None = None,
) -> PackageExportResult:
    """Clone the reference package and apply the supplied canonical plan."""

    source_path = Path(template_path) if template_path is not None else default_template_path()
    source_path = source_path.resolve()
    stat = source_path.stat()
    cache_key = (plan.fingerprint, str(source_path), stat.st_mtime_ns, stat.st_size)
    cached = _EXPORT_CACHE.get(cache_key)
    if cached is not None:
        _EXPORT_CACHE.move_to_end(cache_key)
        return cached

    currency_changes = generate_cell_changes(plan.currency_cells)
    calculator_changes = generate_cell_changes(plan.calculator_cells)
    with ZipFile(source_path, "r") as source:
        replacements = {
            _CURR_SHEET_PART: patch_worksheet_xml(
                source.read(_CURR_SHEET_PART).decode("utf-8"),
                currency_changes,
                dimension_ref="B1:C13",
            ).encode("utf-8"),
            _KALK_SHEET_PART: patch_worksheet_xml(
                source.read(_KALK_SHEET_PART).decode("utf-8"),
                calculator_changes,
                hidden_rows=set(range(plan.visible_data_end_row + 1, 100)),
            ).encode("utf-8"),
            _WORKBOOK_PART: patch_workbook_calculation_properties(
                source.read(_WORKBOOK_PART).decode("utf-8"),
                dict(plan.calculation_properties),
            ).encode("utf-8"),
            _WORKBOOK_RELS_PART: remove_calc_chain_relationship(
                source.read(_WORKBOOK_RELS_PART).decode("utf-8")
            ).encode("utf-8"),
            _CONTENT_TYPES_PART: remove_calc_chain_content_type(
                source.read(_CONTENT_TYPES_PART).decode("utf-8")
            ).encode("utf-8"),
        }
        if plan.source_provenance or plan.date_metadata_json:
            custom_xml = source.read(_CUSTOM_PROPERTIES_PART).decode("utf-8")
            custom_xml = patch_custom_properties_xml(custom_xml, plan.source_provenance)
            custom_xml = patch_date_metadata_xml(custom_xml, plan.date_metadata_json)
            replacements[_CUSTOM_PROPERTIES_PART] = custom_xml.encode("utf-8")
        content = clone_xlsx_package(source, replacements, deleted_parts=_DELETED_PARTS)

    changed_parts = _BASE_CHANGED_PARTS + (
        (_CUSTOM_PROPERTIES_PART,) if plan.source_provenance or plan.date_metadata_json else ()
    )
    result = PackageExportResult(content=content, changed_parts=changed_parts, deleted_parts=_DELETED_PARTS)
    _EXPORT_CACHE[cache_key] = result
    _EXPORT_CACHE.move_to_end(cache_key)
    while len(_EXPORT_CACHE) > _EXPORT_CACHE_LIMIT:
        _EXPORT_CACHE.popitem(last=False)
    return result


def clear_workbook_package_export_cache() -> None:
    """Clear the bounded in-process package cache used by tests and diagnostics."""

    _EXPORT_CACHE.clear()
