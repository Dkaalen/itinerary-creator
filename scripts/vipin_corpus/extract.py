"""Extract itinerary-like rows from Vipin Excel workbooks."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Iterable, Mapping

from scripts.vipin_corpus.constants import DAY_RE, HEADER_ALIASES, MAIN_NS, REL_NS
from scripts.vipin_corpus.models import ExcelCorpusItem
from scripts.vipin_corpus.text import _norm, _norm_key


def _col_to_idx(ref: str) -> int:
    match = re.match(r"([A-Z]+)", ref or "")
    if not match:
        return 0
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - 64
    return value


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    strings: list[str] = []
    with zf.open("xl/sharedStrings.xml") as handle:
        for _event, elem in ET.iterparse(handle, events=("end",)):
            if elem.tag == MAIN_NS + "si":
                strings.append("".join(text.text or "" for text in elem.iter(MAIN_NS + "t")))
                elem.clear()
    return strings


def _workbook_sheets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("pr:Relationship", rel_ns)}
    sheets: list[tuple[str, str]] = []
    sheets_el = workbook.find("a:sheets", ns)
    if sheets_el is None:
        return []
    for sheet in sheets_el:
        name = sheet.attrib.get("name", "Sheet")
        target = rel_map.get(sheet.attrib.get(REL_NS, ""), "")
        if target and not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        if target:
            sheets.append((name, target))
    return sheets


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        value = cell.find(MAIN_NS + "v")
        if value is None or value.text is None:
            return ""
        try:
            return shared_strings[int(value.text)]
        except (ValueError, IndexError):
            return value.text or ""
    if cell_type == "inlineStr":
        inline = cell.find(MAIN_NS + "is")
        return "" if inline is None else "".join(text.text or "" for text in inline.iter(MAIN_NS + "t"))
    value = cell.find(MAIN_NS + "v")
    return "" if value is None else (value.text or "")


def _parse_rows(
    zf: zipfile.ZipFile,
    target: str,
    shared_strings: list[str],
    *,
    max_rows: int = 130,
    max_cols: int = 25,
) -> dict[int, dict[int, str]]:
    rows: dict[int, dict[int, str]] = defaultdict(dict)
    with zf.open(target) as handle:
        for _event, row in ET.iterparse(handle, events=("end",)):
            if row.tag != MAIN_NS + "row":
                continue
            row_index = int(row.attrib.get("r", "0") or 0)
            if row_index > max_rows:
                break
            for cell in row.findall(MAIN_NS + "c"):
                col = _col_to_idx(cell.attrib.get("r", ""))
                if not col or col > max_cols:
                    continue
                value = _norm(_cell_value(cell, shared_strings))
                if value:
                    rows[row_index][col] = value
            row.clear()
    return rows


def _find_header_rows(rows: Mapping[int, Mapping[int, str]]) -> list[tuple[int, int, dict[int, str]]]:
    candidates: list[tuple[int, int, dict[int, str]]] = []
    for row_index, cols in rows.items():
        labels = {col: _norm_key(value) for col, value in cols.items()}
        values = list(labels.values())
        score = 0
        if any(value == "day" for value in values):
            score += 2
        if any(value == "type" for value in values):
            score += 2
        if any(value in HEADER_ALIASES["city"] for value in values):
            score += 1
        if any(value in HEADER_ALIASES["element"] for value in values):
            score += 2
        if any(value in (HEADER_ALIASES["from_date"] | HEADER_ALIASES["to_date"] | HEADER_ALIASES["nights"]) for value in values):
            score += 1
        if score >= 4:
            candidates.append((row_index, score, labels))
    return sorted(candidates, key=lambda item: (-item[1], item[0]))


def _map_headers(labels: Mapping[int, str]) -> dict[str, int]:
    mapped: dict[str, int] = {}
    for col, value in labels.items():
        for key, aliases in HEADER_ALIASES.items():
            if value in aliases:
                mapped.setdefault(key, col)
                break
    return mapped


def _looks_itinerary_like(day: str, row_type: str, element: str, city: str) -> bool:
    if not any([day, row_type, element, city]):
        return False
    return bool(DAY_RE.search(day) or row_type)


def collect_excel_corpus_items(paths: Iterable[str | Path]) -> list[ExcelCorpusItem]:
    """Extract itinerary-like calculator rows from the supplied workbook paths."""

    items: list[ExcelCorpusItem] = []
    for path_value in paths:
        path = Path(path_value)
        with zipfile.ZipFile(path) as zf:
            shared_strings = _load_shared_strings(zf)
            for sheet_name, target in _workbook_sheets(zf):
                rows = _parse_rows(zf, target, shared_strings)
                header_rows = _find_header_rows(rows)
                if not header_rows:
                    continue
                header_row, _score, labels = header_rows[0]
                headers = _map_headers(labels)
                if "day" not in headers or "type" not in headers:
                    continue
                for row_number in sorted(rows):
                    if row_number <= header_row:
                        continue
                    values = rows[row_number]
                    day = _norm(values.get(headers.get("day", -1), ""))
                    row_type = _norm(values.get(headers.get("type", -1), ""))
                    city = _norm(values.get(headers.get("city", -1), "")) if "city" in headers else ""
                    element = _norm(values.get(headers.get("element", -1), "")) if "element" in headers else ""
                    if not _looks_itinerary_like(day, row_type, element, city):
                        continue
                    items.append(ExcelCorpusItem(
                        file=path.name,
                        sheet=sheet_name,
                        row=row_number,
                        day=day,
                        row_type=row_type,
                        city=city,
                        element=element,
                        nights=_norm(values.get(headers.get("nights", -1), "")) if "nights" in headers else "",
                        from_date=_norm(values.get(headers.get("from_date", -1), "")) if "from_date" in headers else "",
                        to_date=_norm(values.get(headers.get("to_date", -1), "")) if "to_date" in headers else "",
                        supplier=_norm(values.get(headers.get("supplier", -1), "")) if "supplier" in headers else "",
                    ))
    return items
