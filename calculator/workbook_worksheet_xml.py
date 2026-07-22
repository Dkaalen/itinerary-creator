"""Mutate worksheet XML using validated package cell changes."""

from __future__ import annotations

import re
from typing import Mapping
from xml.sax.saxutils import escape

from calculator.numeric_input import parse_decimal_input_strict
from calculator.workbook_package_cell_changes import PackageCellChange

_CELL_RE = re.compile(r'<c\b(?P<attrs>[^>]*?\br="(?P<ref>[A-Z]+\d+)"[^>]*?)\s*(?:/>|>(?P<body>.*?)</c>)', re.DOTALL)
_ROW_RE = re.compile(r'(?P<open><row\b[^>]*?\br="(?P<row>\d+)"[^>]*>)(?P<body>.*?)(?P<close></row>)', re.DOTALL)
_TYPE_ATTR_RE = re.compile(r'\s+t="[^"]*"')


def patch_worksheet_xml(
    xml: str,
    changes: Mapping[str, PackageCellChange],
    *,
    dimension_ref: str | None = None,
    hidden_rows: set[int] | None = None,
) -> str:
    """Apply all requested cells in one worksheet pass."""

    patched = _patch_cells(xml, changes)
    if hidden_rows is not None:
        patched = _patch_hidden_rows(patched, hidden_rows)
    if dimension_ref is not None:
        patched = re.sub(
            r'<dimension\s+ref="[^"]+"\s*/>',
            f'<dimension ref="{dimension_ref}"/>',
            patched,
            count=1,
        )
    return patched



def _patch_hidden_rows(xml: str, hidden_rows: set[int]) -> str:
    """Set row visibility deterministically for Calculator data rows."""

    def replace(match: re.Match[str]) -> str:
        row_number = int(match.group("row"))
        open_tag = match.group("open")
        if DATA_ROW_MIN <= row_number <= DATA_ROW_MAX:
            open_tag = re.sub(r'\s+hidden="[^"]*"', "", open_tag)
            if row_number in hidden_rows:
                open_tag = open_tag[:-1] + ' hidden="1">'
        return open_tag + match.group("body") + match.group("close")

    return _ROW_RE.sub(replace, xml)


DATA_ROW_MIN = 7
DATA_ROW_MAX = 99


def _patch_cells(xml: str, changes: Mapping[str, PackageCellChange]) -> str:
    """Patch cells linearly by grouping requested changes per worksheet row."""

    by_row: dict[int, dict[str, PackageCellChange]] = {}
    for ref, change in changes.items():
        row_match = re.search(r"\d+$", ref)
        if row_match is None:
            raise ValueError(f"Invalid cell reference: {ref}")
        row_number = int(row_match.group())
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
    changes: Mapping[str, PackageCellChange],
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
            output.append(
                _cell_fragment(
                    ref,
                    cell_match.group("attrs"),
                    change.value,
                    change.kind,
                )
            )
            emitted.add(ref)
        cursor = cell_match.end()
    output.append(body[cursor:])

    missing = [
        (ref, change)
        for ref, change in changes.items()
        if ref not in emitted and not (change.value is None and change.kind == "blank")
    ]
    if missing:
        fragments = [
            _cell_fragment(ref, f' r="{ref}"', change.value, change.kind)
            for ref, change in sorted(missing, key=lambda item: _cell_ref_sort_key(item[0]))
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


def _new_row_fragment(row_number: int, changes: Mapping[str, PackageCellChange]) -> str:
    cells = [
        _cell_fragment(ref, f' r="{ref}"', change.value, change.kind)
        for ref, change in sorted(changes.items(), key=lambda item: _cell_ref_sort_key(item[0]))
        if not (change.value is None and change.kind == "blank")
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
