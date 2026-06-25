"""Read source XLSX XML and build the Iceland reference payload."""

import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from scripts.reference_corpus_build.common import CORPUS_VERSION, SCHEMA_VERSION, TARGET_ICELAND_SHEETS, sha256

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
CELL_REF_RE = re.compile(r"([A-Z]+)")


def xlsx_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist(): return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in item.iter(NS + "t")) for item in root.findall(NS + "si")]


def xlsx_sheet_paths(archive: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml")); relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels")); relation_map = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}; paths = {}
    sheets = workbook.find(NS + "sheets")
    for sheet in tuple(sheets) if sheets is not None else ():
        target = relation_map[sheet.attrib[REL_NS + "id"]].lstrip("/"); paths[sheet.attrib["name"]] = target if target.startswith("xl/") else f"xl/{target}"
    return paths


def xlsx_rows(archive: ZipFile, sheet_path: str, shared_strings: list[str]) -> list[tuple[int, dict[str, str]]]:
    root = ET.fromstring(archive.read(sheet_path)); output = []
    for row in root.findall(f".//{NS}sheetData/{NS}row"):
        values = {}
        for cell in row.findall(NS + "c"):
            match = CELL_REF_RE.match(cell.attrib.get("r", ""))
            if not match: continue
            kind, node = cell.attrib.get("t"), cell.find(NS + "v")
            if kind == "inlineStr": value = "".join(item.text or "" for item in cell.iter(NS + "t"))
            elif node is None: value = ""
            elif kind == "s": value = shared_strings[int(node.text or "0")]
            else: value = node.text or ""
            values[match.group(1)] = value
        output.append((int(row.attrib["r"]), values))
    return output


def sheet_contract(name: str) -> tuple[str, str, int]:
    match = re.fullmatch(r"(\d+)D\s+(SD|GTS|GTW)", name)
    if not match: raise ValueError(f"unsupported reference sheet: {name}")
    code = match.group(2)
    return ("self_drive" if code == "SD" else "group_tour", "summer" if code in {"SD", "GTS"} else "winter", int(match.group(1)))


def build_iceland_reference(source_path: Path, output_path: Path) -> tuple[int, int]:
    with ZipFile(source_path) as archive:
        shared, paths = xlsx_shared_strings(archive), xlsx_sheet_paths(archive); missing = [name for name in TARGET_ICELAND_SHEETS if name not in paths]
        if missing: raise ValueError(f"Iceland workbook is missing sheets: {', '.join(missing)}")
        sheets, total = [], 0
        for name in TARGET_ICELAND_SHEETS:
            kind, season, duration = sheet_contract(name); worksheet = xlsx_rows(archive, paths[name], shared); by_number = dict(worksheet)
            metadata = {"season": (by_number.get(1, {}).get("B") or "").removeprefix("Season:").strip(), "tour_url": (by_number.get(2, {}).get("B") or "").removeprefix("Tour:").strip(), "pax": (by_number.get(3, {}).get("B") or "").removeprefix("Pax:").strip(), "rooming": (by_number.get(4, {}).get("B") or "").removeprefix("Rooming:").strip()}
            headers = {column: re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") for column, value in by_number.get(6, {}).items() if value.strip()}; rows = []
            for excel_row, values in worksheet:
                if excel_row < 7: continue
                if not (values.get("D") or "").strip() and not (values.get("J") or "").strip(): continue
                record = {"excel_row": excel_row}; record.update({field: value.strip() for column, field in headers.items() if (value := values.get(column) or "").strip()}); rows.append(record)
            total += len(rows); sheets.append({"sheet_name": name, "itinerary_kind": kind, "season": season, "duration_days": duration, "metadata": metadata, "rows": rows})
    payload = {"schema_version": SCHEMA_VERSION, "corpus_version": CORPUS_VERSION, "source": {"filename": source_path.name, "sha256": sha256(source_path), "included_sheet_codes": ["SD", "GTS", "GTW"], "excluded_sheet_codes": ["RS", "RW", "Kalk"]}, "sheets": sheets}
    output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(sheets), total
