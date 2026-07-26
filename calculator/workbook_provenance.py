"""Internal XLSX provenance metadata for Local Library sourced rows."""
from __future__ import annotations

from dataclasses import asdict
import json
from xml.etree import ElementTree as ET

from calculator.workbook_export_plan import ExportSourceProvenance

CUSTOM_PROPERTY_NAME = "BooknordicsLocalLibraryProvenance"
_CUSTOM_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
_VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
_FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"

ET.register_namespace("", _CUSTOM_NS)
ET.register_namespace("vt", _VT_NS)


def provenance_json(items: tuple[ExportSourceProvenance, ...]) -> str:
    """Return deterministic compact JSON for internal workbook metadata."""

    return json.dumps(
        [asdict(item) for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def patch_custom_properties_xml(
    xml: str,
    items: tuple[ExportSourceProvenance, ...],
) -> str:
    """Set or remove the Booknordics provenance custom property."""

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

    if not items:
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
    ET.SubElement(prop, value_tag).text = provenance_json(items)
    return _serialize(root)


def _serialize(root: ET.Element) -> str:
    body = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body


__all__ = [
    "CUSTOM_PROPERTY_NAME",
    "patch_custom_properties_xml",
    "provenance_json",
]
