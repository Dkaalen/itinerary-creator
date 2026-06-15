"""Build the versioned itinerary reference corpus from supplied source files.

This is an offline maintenance utility.  It deliberately uses only the Python
standard library so the project can rebuild the corpus without adding a runtime
spreadsheet dependency.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from place_aliases import canonicalize_place_name

CORPUS_VERSION = "ih1-v1"
SCHEMA_VERSION = 1
TARGET_ICELAND_SHEETS = tuple(
    f"{days}D {kind}"
    for kind in ("SD", "GTS", "GTW")
    for days in (5, 6, 7, 8, 10)
)

_XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_XLSX_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_CELL_REF_RE = re.compile(r"([A-Z]+)")
_PLACEHOLDER_RE = re.compile(r"\[([^\[\]]+)\]")
_CONDITIONAL_MARKERS = (
    "if snow",
    "weather permitting",
    "depending on weather",
    "subject to weather",
    "not guaranteed",
    "upon request",
    "on request",
    "if needed",
    "where included",
    "subject to availability",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_place(value: str) -> str:
    return canonicalize_place_name(value) or str(value or "").strip()


def _write_tsv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_three_column_source(path: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not raw_line.strip():
            continue
        parts = raw_line.split("\t", 2)
        if len(parts) != 3:
            raise ValueError(f"{path.name} line {line_number} does not contain three tab-separated fields")
        rows.append(tuple(part.strip() for part in parts))
    return rows


def build_standard_templates(source_path: Path, output_path: Path) -> int:
    output: list[dict[str, str]] = []
    for index, (service_type, destination, template_text) in enumerate(
        _read_three_column_source(source_path), start=1
    ):
        placeholders = sorted({match.strip() for match in _PLACEHOLDER_RE.findall(template_text)})
        output.append(
            {
                "record_id": f"standard-{index:04d}",
                "service_type": service_type,
                "source_destination": destination,
                "canonical_destination": _canonical_place(destination),
                "template_text": template_text,
                "placeholders": ";".join(placeholders),
            }
        )
    _write_tsv(
        output_path,
        (
            "record_id",
            "service_type",
            "source_destination",
            "canonical_destination",
            "placeholders",
            "template_text",
        ),
        output,
    )
    return len(output)


def _activity_location(activity_text: str) -> str:
    prefix, separator, _ = activity_text.partition(":")
    return prefix.strip() if separator else ""


def _conditional_markers(text: str) -> str:
    lower = text.lower()
    return ";".join(marker for marker in _CONDITIONAL_MARKERS if marker in lower)


def build_clean_activities(source_path: Path, output_path: Path) -> int:
    output: list[dict[str, str]] = []
    for index, (record_type, source_city, activity_text) in enumerate(
        _read_three_column_source(source_path), start=1
    ):
        location = _activity_location(activity_text)
        output.append(
            {
                "record_id": f"activity-{index:04d}",
                "record_type": record_type,
                "source_city": source_city,
                "canonical_city": _canonical_place(source_city),
                "activity_location": location,
                "canonical_activity_location": _canonical_place(location),
                "activity_text": activity_text,
                "conditional_markers": _conditional_markers(activity_text),
            }
        )
    _write_tsv(
        output_path,
        (
            "record_id",
            "record_type",
            "source_city",
            "canonical_city",
            "activity_location",
            "canonical_activity_location",
            "conditional_markers",
            "activity_text",
        ),
        output,
    )
    return len(output)


def _xlsx_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in item.iter(_XLSX_NS + "t")) for item in root.findall(_XLSX_NS + "si")]


def _xlsx_sheet_paths(archive: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationship_map = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
    paths: dict[str, str] = {}
    sheets_node = workbook.find(_XLSX_NS + "sheets")
    for sheet in tuple(sheets_node) if sheets_node is not None else ():
        relationship_id = sheet.attrib[_XLSX_REL_NS + "id"]
        target = relationship_map[relationship_id].lstrip("/")
        paths[sheet.attrib["name"]] = target if target.startswith("xl/") else f"xl/{target}"
    return paths


def _xlsx_rows(archive: ZipFile, sheet_path: str, shared_strings: list[str]) -> list[tuple[int, dict[str, str]]]:
    root = ET.fromstring(archive.read(sheet_path))
    output: list[tuple[int, dict[str, str]]] = []
    for row in root.findall(f".//{_XLSX_NS}sheetData/{_XLSX_NS}row"):
        values: dict[str, str] = {}
        for cell in row.findall(_XLSX_NS + "c"):
            reference = cell.attrib.get("r", "")
            match = _CELL_REF_RE.match(reference)
            if not match:
                continue
            column = match.group(1)
            cell_type = cell.attrib.get("t")
            value_node = cell.find(_XLSX_NS + "v")
            if cell_type == "inlineStr":
                value = "".join(node.text or "" for node in cell.iter(_XLSX_NS + "t"))
            elif value_node is None:
                value = ""
            elif cell_type == "s":
                value = shared_strings[int(value_node.text or "0")]
            else:
                value = value_node.text or ""
            values[column] = value
        output.append((int(row.attrib["r"]), values))
    return output


def _sheet_contract(sheet_name: str) -> tuple[str, str, int]:
    match = re.fullmatch(r"(\d+)D\s+(SD|GTS|GTW)", sheet_name)
    if not match:
        raise ValueError(f"unsupported reference sheet: {sheet_name}")
    duration = int(match.group(1))
    code = match.group(2)
    kind = "self_drive" if code == "SD" else "group_tour"
    season = "summer" if code in {"SD", "GTS"} else "winter"
    return kind, season, duration


def build_iceland_reference(source_path: Path, output_path: Path) -> tuple[int, int]:
    with ZipFile(source_path) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheet_paths = _xlsx_sheet_paths(archive)
        missing = [name for name in TARGET_ICELAND_SHEETS if name not in sheet_paths]
        if missing:
            raise ValueError(f"Iceland workbook is missing sheets: {', '.join(missing)}")

        sheets: list[dict[str, object]] = []
        total_rows = 0
        for sheet_name in TARGET_ICELAND_SHEETS:
            kind, season, duration = _sheet_contract(sheet_name)
            worksheet_rows = _xlsx_rows(archive, sheet_paths[sheet_name], shared_strings)
            by_number = {number: values for number, values in worksheet_rows}
            metadata = {
                "season": (by_number.get(1, {}).get("B") or "").removeprefix("Season:").strip(),
                "tour_url": (by_number.get(2, {}).get("B") or "").removeprefix("Tour:").strip(),
                "pax": (by_number.get(3, {}).get("B") or "").removeprefix("Pax:").strip(),
                "rooming": (by_number.get(4, {}).get("B") or "").removeprefix("Rooming:").strip(),
            }
            header_values = by_number.get(6, {})
            header_by_column = {
                column: re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
                for column, value in header_values.items()
                if value.strip()
            }
            rows: list[dict[str, str | int]] = []
            for excel_row, values in worksheet_rows:
                if excel_row < 7:
                    continue
                row_type = (values.get("D") or "").strip()
                travel_element = (values.get("J") or "").strip()
                if not row_type and not travel_element:
                    continue
                record: dict[str, str | int] = {"excel_row": excel_row}
                for column, field_name in header_by_column.items():
                    value = (values.get(column) or "").strip()
                    if value:
                        record[field_name] = value
                rows.append(record)
            total_rows += len(rows)
            sheets.append(
                {
                    "sheet_name": sheet_name,
                    "itinerary_kind": kind,
                    "season": season,
                    "duration_days": duration,
                    "metadata": metadata,
                    "rows": rows,
                }
            )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "corpus_version": CORPUS_VERSION,
        "source": {
            "filename": source_path.name,
            "sha256": _sha256(source_path),
            "included_sheet_codes": ["SD", "GTS", "GTW"],
            "excluded_sheet_codes": ["RS", "RW", "Kalk"],
        },
        "sheets": sheets,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(sheets), total_rows


def build_manifest(
    output_dir: Path,
    *,
    standard_source: Path,
    activity_source: Path,
    iceland_source: Path,
    standard_count: int,
    activity_count: int,
    iceland_sheet_count: int,
    iceland_row_count: int,
) -> None:
    files = {
        "standard_input_templates.tsv": standard_count,
        "clean_activity_inputs.tsv": activity_count,
        "iceland_standard_itinerary.json": iceland_row_count,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "corpus_version": CORPUS_VERSION,
        "files": [
            {
                "name": name,
                "record_count": count,
                "sha256": _sha256(output_dir / name),
            }
            for name, count in files.items()
        ],
        "source_files": [
            {"name": standard_source.name, "sha256": _sha256(standard_source)},
            {"name": activity_source.name, "sha256": _sha256(activity_source)},
            {"name": iceland_source.name, "sha256": _sha256(iceland_source)},
        ],
        "iceland_sheet_count": iceland_sheet_count,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standard-inputs", required=True, type=Path)
    parser.add_argument("--activities", required=True, type=Path)
    parser.add_argument("--iceland-workbook", required=True, type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("itinerary_generation/data/reference_corpus") / CORPUS_VERSION,
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    standard_count = build_standard_templates(
        args.standard_inputs,
        args.output_dir / "standard_input_templates.tsv",
    )
    activity_count = build_clean_activities(
        args.activities,
        args.output_dir / "clean_activity_inputs.tsv",
    )
    iceland_sheet_count, iceland_row_count = build_iceland_reference(
        args.iceland_workbook,
        args.output_dir / "iceland_standard_itinerary.json",
    )
    build_manifest(
        args.output_dir,
        standard_source=args.standard_inputs,
        activity_source=args.activities,
        iceland_source=args.iceland_workbook,
        standard_count=standard_count,
        activity_count=activity_count,
        iceland_sheet_count=iceland_sheet_count,
        iceland_row_count=iceland_row_count,
    )
    print(
        f"Built {CORPUS_VERSION}: {standard_count} standard templates, "
        f"{activity_count} activities, {iceland_sheet_count} Iceland sheets / "
        f"{iceland_row_count} rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
