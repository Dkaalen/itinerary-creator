"""Internal XLSX metadata for Calculator trip-date relationships."""

from __future__ import annotations

from dataclasses import replace
import json
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET

from calculator.calculator_state import CalculatorState
from calculator.date_links import initialize_date_relationships
from calculator.row_model import CalculatorRow

CUSTOM_PROPERTY_NAME = "BooknordicsCalculatorDateLinks"
_CUSTOM_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
_VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
_FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"
_METADATA_VERSION = 1

ET.register_namespace("", _CUSTOM_NS)
ET.register_namespace("vt", _VT_NS)


def date_metadata_json(state: CalculatorState) -> str:
    """Return deterministic compact JSON for persisted date-link ownership."""

    trip_start_date, rows = initialize_date_relationships(state.rows, state.trip_start_date)
    payload = {
        "version": _METADATA_VERSION,
        "trip_start_date": trip_start_date,
        "rows": [
            {
                "row_id": str(row.row_id or ""),
                "from_date_mode": str(row.from_date_mode or ""),
                "from_date_offset": row.from_date_offset,
                "to_date_mode": str(row.to_date_mode or ""),
                "to_date_offset": row.to_date_offset,
            }
            for row in rows
            if row.row_id and (
                row.from_date_mode
                or row.from_date_offset is not None
                or row.to_date_mode
                or row.to_date_offset is not None
            )
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def patch_date_metadata_xml(xml: str, metadata_json: str) -> str:
    """Set or remove the Booknordics Calculator date metadata property."""

    root = ET.fromstring(xml)
    property_tag = f"{{{_CUSTOM_NS}}}property"
    value_tag = f"{{{_VT_NS}}}lpwstr"
    existing = None
    max_pid = 1
    for prop in root.findall(property_tag):
        try:
            max_pid = max(max_pid, int(prop.attrib.get("pid", "1")))
        except ValueError:
            pass
        if prop.attrib.get("name") == CUSTOM_PROPERTY_NAME:
            existing = prop

    if not metadata_json:
        if existing is not None:
            root.remove(existing)
        return _serialize(root)

    prop = existing
    if prop is None:
        prop = ET.SubElement(
            root,
            property_tag,
            {"fmtid": _FMTID, "pid": str(max_pid + 1), "name": CUSTOM_PROPERTY_NAME},
        )
    else:
        for child in list(prop):
            prop.remove(child)
    ET.SubElement(prop, value_tag).text = metadata_json
    return _serialize(root)


def read_date_metadata_xml(xml: bytes | str) -> Mapping[str, Any] | None:
    """Return validated date metadata from custom-properties XML."""

    root = ET.fromstring(xml)
    property_tag = f"{{{_CUSTOM_NS}}}property"
    for prop in root.findall(property_tag):
        if prop.attrib.get("name") != CUSTOM_PROPERTY_NAME:
            continue
        text = "".join(prop.itertext()).strip()
        if not text:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, Mapping) or int(payload.get("version") or 0) != _METADATA_VERSION:
            return None
        return payload
    return None


def apply_date_metadata(
    rows: Sequence[CalculatorRow],
    metadata: Mapping[str, Any] | None,
) -> tuple[str, tuple[CalculatorRow, ...]]:
    """Apply workbook metadata, falling back to safe relationship inference."""

    if not metadata:
        return initialize_date_relationships(rows)
    by_id: dict[str, Mapping[str, Any]] = {}
    for item in metadata.get("rows") or ():
        if isinstance(item, Mapping) and item.get("row_id") is not None:
            by_id[str(item.get("row_id") or "")] = item
    prepared: list[CalculatorRow] = []
    for row in rows:
        item = by_id.get(str(row.row_id or ""))
        if not item:
            prepared.append(row)
            continue
        prepared.append(
            replace(
                row,
                from_date_mode=_mode(item.get("from_date_mode")),
                from_date_offset=_offset(item.get("from_date_offset")),
                to_date_mode=_mode(item.get("to_date_mode")),
                to_date_offset=_offset(item.get("to_date_offset")),
            )
        )
    return initialize_date_relationships(
        prepared,
        str(metadata.get("trip_start_date") or ""),
    )


def _mode(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"linked", "locked"} else ""


def _offset(value: object) -> int | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _serialize(root: ET.Element) -> str:
    body = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body


__all__ = [
    "CUSTOM_PROPERTY_NAME",
    "apply_date_metadata",
    "date_metadata_json",
    "patch_date_metadata_xml",
    "read_date_metadata_xml",
]
