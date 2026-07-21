"""Apply a canonical calculator export plan to the reference XLSX package.

The workbook is an immutable visual/structural template. This renderer owns
only package/XML mechanics; every calculator-to-cell decision comes from
:mod:`calculator.workbook_export_plan`.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from typing import Mapping
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from calculator.numeric_input import parse_decimal_input_strict
from calculator.template_structure import default_template_path
from calculator.workbook_export_plan import ExportCell, WorkbookExportPlan

_CURR_SHEET_PART = "xl/worksheets/sheet1.xml"
_KALK_SHEET_PART = "xl/worksheets/sheet2.xml"
_WORKBOOK_PART = "xl/workbook.xml"
_CELL_RE = re.compile(r'<c\b(?P<attrs>[^>]*?\br="(?P<ref>[A-Z]+\d+)"[^>]*?)\s*(?:/>|>(?P<body>.*?)</c>)', re.DOTALL)
_ROW_RE = re.compile(r'(?P<open><row\b[^>]*?\br="(?P<row>\d+)"[^>]*>)(?P<body>.*?)(?P<close></row>)', re.DOTALL)
_TYPE_ATTR_RE = re.compile(r'\s+t="[^"]*"')
_EXPORT_CACHE_LIMIT = 2
_EXPORT_CACHE: OrderedDict[tuple[str, str, int, int], "PackageExportResult"] = OrderedDict()


@dataclass(frozen=True)
class PackageExportResult:
    """Exact-reference XLSX bytes and the package parts intentionally changed."""

    content: bytes
    changed_parts: tuple[str, ...]


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

    with ZipFile(source_path, "r") as source:
        curr_xml = source.read(_CURR_SHEET_PART).decode("utf-8")
        kalk_xml = source.read(_KALK_SHEET_PART).decode("utf-8")
        workbook_xml = source.read(_WORKBOOK_PART).decode("utf-8")
        curr_xml = _patch_currency_sheet(curr_xml, plan.currency_cells)
        kalk_xml = _patch_kalk_sheet(kalk_xml, plan.calculator_cells)
        workbook_xml = _patch_workbook_calculation_properties(
            workbook_xml,
            dict(plan.calculation_properties),
        )

        replacements = {
            _CURR_SHEET_PART: curr_xml.encode("utf-8"),
            _KALK_SHEET_PART: kalk_xml.encode("utf-8"),
            _WORKBOOK_PART: workbook_xml.encode("utf-8"),
        }
        buffer = BytesIO()
        with ZipFile(buffer, "w") as target:
            for info in source.infolist():
                data = replacements.get(info.filename)
                if data is None:
                    data = source.read(info.filename)
                target.writestr(_clone_zip_info(info), data)

    result = PackageExportResult(
        content=buffer.getvalue(),
        changed_parts=(_CURR_SHEET_PART, _KALK_SHEET_PART, _WORKBOOK_PART),
    )
    _EXPORT_CACHE[cache_key] = result
    _EXPORT_CACHE.move_to_end(cache_key)
    while len(_EXPORT_CACHE) > _EXPORT_CACHE_LIMIT:
        _EXPORT_CACHE.popitem(last=False)
    return result


def clear_workbook_package_export_cache() -> None:
    """Clear the bounded in-process package cache used by tests and diagnostics."""

    _EXPORT_CACHE.clear()


def _patch_workbook_calculation_properties(xml: str, properties: Mapping[str, object]) -> str:
    """Apply calculation properties while preserving workbook metadata."""

    match = re.search(r"<calcPr\b(?P<attrs>[^>]*)/>", xml)
    if not match:
        raise ValueError("Reference workbook is missing calcPr metadata.")
    attrs = match.group("attrs")
    for name, raw_value in properties.items():
        value = "1" if raw_value is True else "0" if raw_value is False else str(raw_value)
        pattern = re.compile(rf'\s+{re.escape(name)}="[^"]*"')
        replacement = f' {name}="{value}"'
        if pattern.search(attrs):
            attrs = pattern.sub(replacement, attrs, count=1)
        else:
            attrs += replacement
    replacement = f"<calcPr{attrs}/>"
    return xml[: match.start()] + replacement + xml[match.end() :]


def _patch_currency_sheet(xml: str, cells: tuple[ExportCell, ...]) -> str:
    patched = _patch_cells(xml, _cell_changes(cells))
    return re.sub(r'<dimension\s+ref="[^"]+"\s*/>', '<dimension ref="B1:C13"/>', patched, count=1)


def _patch_kalk_sheet(xml: str, cells: tuple[ExportCell, ...]) -> str:
    return _patch_cells(xml, _cell_changes(cells))


def _cell_changes(cells: tuple[ExportCell, ...]) -> dict[str, tuple[object, str]]:
    return {cell.reference: (cell.value, cell.kind) for cell in cells}


def _patch_cells(xml: str, changes: Mapping[str, tuple[object, str]]) -> str:
    """Patch all requested cells in one worksheet pass.

    The previous implementation rescanned the complete worksheet XML once per
    cell. A normal export updates thousands of cells, so that quadratic pattern
    dominated download time. Grouping changes by row keeps the exact template
    package contract while making export linear in worksheet size.
    """

    by_row: dict[int, dict[str, tuple[object, str]]] = {}
    for ref, change in changes.items():
        row_number = int(re.search(r"\d+$", ref).group())
        by_row.setdefault(row_number, {})[ref] = change

    sheet_data = re.search(r'(<sheetData>)(?P<body>.*?)(</sheetData>)', xml, re.DOTALL)
    if not sheet_data:
        raise ValueError("Reference workbook is missing sheetData.")

    body = sheet_data.group("body")
    output: list[str] = []
    cursor = 0
    emitted_rows: set[int] = set()
    changed_row_numbers = tuple(sorted(by_row))
    for row_match in _ROW_RE.finditer(body):
        row_number = int(row_match.group("row"))
        output.append(body[cursor:row_match.start()])
        for missing_row in changed_row_numbers:
            if missing_row >= row_number:
                break
            if missing_row not in emitted_rows:
                output.append(_new_row_fragment(missing_row, by_row[missing_row]))
                emitted_rows.add(missing_row)
        row_changes = by_row.get(row_number)
        if row_changes:
            output.append(_patched_row_fragment(row_match, row_changes))
            emitted_rows.add(row_number)
        else:
            output.append(row_match.group(0))
        cursor = row_match.end()

    for missing_row in changed_row_numbers:
        if missing_row not in emitted_rows:
            output.append(_new_row_fragment(missing_row, by_row[missing_row]))
    output.append(body[cursor:])

    new_body = "".join(output)
    replacement = sheet_data.group(1) + new_body + sheet_data.group(3)
    return xml[: sheet_data.start()] + replacement + xml[sheet_data.end() :]


def _patched_row_fragment(
    row_match: re.Match[str],
    changes: Mapping[str, tuple[object, str]],
) -> str:
    body = row_match.group("body")
    output: list[str] = []
    cursor = 0
    emitted: set[str] = set()
    for cell_match in _CELL_RE.finditer(body):
        output.append(body[cursor:cell_match.start()])
        ref = cell_match.group("ref")
        change = changes.get(ref)
        if change is None:
            output.append(cell_match.group(0))
        else:
            value, value_kind = change
            output.append(_cell_fragment(ref, cell_match.group("attrs"), value, value_kind))
            emitted.add(ref)
        cursor = cell_match.end()
    output.append(body[cursor:])

    missing = [
        (ref, change)
        for ref, change in changes.items()
        if ref not in emitted and not (change[0] is None and change[1] == "blank")
    ]
    if missing:
        fragments = [
            _cell_fragment(ref, f' r="{ref}"', value, value_kind)
            for ref, (value, value_kind) in sorted(missing, key=lambda item: _cell_ref_sort_key(item[0]))
        ]
        patched_body = _merge_missing_cells("".join(output), fragments)
    else:
        patched_body = "".join(output)
    return row_match.group("open") + patched_body + row_match.group("close")


def _merge_missing_cells(body: str, fragments: list[str]) -> str:
    existing = list(_CELL_RE.finditer(body))
    if not existing:
        return body + "".join(fragments)

    additions_by_position: dict[int, list[tuple[tuple[int, int], str]]] = {}
    for fragment in fragments:
        ref_match = re.search(r'\br="([A-Z]+\d+)"', fragment)
        assert ref_match is not None
        target_key = _cell_ref_sort_key(ref_match.group(1))
        insertion = len(body)
        for cell_match in existing:
            if _cell_ref_sort_key(cell_match.group("ref")) > target_key:
                insertion = cell_match.start()
                break
        additions_by_position.setdefault(insertion, []).append((target_key, fragment))

    for insertion in sorted(additions_by_position, reverse=True):
        ordered = "".join(fragment for _, fragment in sorted(additions_by_position[insertion]))
        body = body[:insertion] + ordered + body[insertion:]
    return body


def _new_row_fragment(row_number: int, changes: Mapping[str, tuple[object, str]]) -> str:
    cells = [
        _cell_fragment(ref, f' r="{ref}"', value, value_kind)
        for ref, (value, value_kind) in sorted(changes.items(), key=lambda item: _cell_ref_sort_key(item[0]))
        if not (value is None and value_kind == "blank")
    ]
    return f'<row r="{row_number}">{"".join(cells)}</row>' if cells else ""


def _cell_ref_sort_key(ref: str) -> tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
    if not match:
        raise ValueError(f"Invalid cell reference: {ref}")
    return int(match.group(2)), _column_number(match.group(1))


def _cell_fragment(ref: str, attrs: str, value: object, value_kind: str) -> str:
    clean_attrs = _TYPE_ATTR_RE.sub("", attrs).rstrip().rstrip("/")
    if f'r="{ref}"' not in clean_attrs:
        clean_attrs = f' r="{ref}"' + clean_attrs
    if value is None or value_kind == "blank":
        return f"<c{clean_attrs}/>"
    if value_kind == "text":
        text = escape(str(value), {'"': "&quot;"})
        return f'<c{clean_attrs} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'
    if value_kind == "boolean":
        return f'<c{clean_attrs} t="b"><v>{1 if bool(value) else 0}</v></c>'
    if value_kind == "formula":
        formula = escape(str(value).strip().lstrip("="))
        return f"<c{clean_attrs}><f>{formula}</f></c>"
    return f"<c{clean_attrs}><v>{_number_text(value)}</v></c>"


def _number_text(value: object) -> str:
    decimal = parse_decimal_input_strict(value, allow_blank=False)
    assert decimal is not None
    text = format(decimal, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _column_number(letters: str) -> int:
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - ord("A") + 1
    return value


def _clone_zip_info(info: ZipInfo) -> ZipInfo:
    clone = ZipInfo(info.filename, date_time=info.date_time)
    clone.compress_type = info.compress_type if info.compress_type is not None else ZIP_DEFLATED
    clone.comment = info.comment
    clone.extra = info.extra
    clone.internal_attr = info.internal_attr
    clone.external_attr = info.external_attr
    clone.create_system = info.create_system
    clone.create_version = info.create_version
    clone.extract_version = info.extract_version
    clone.flag_bits = info.flag_bits
    clone.volume = info.volume
    return clone
