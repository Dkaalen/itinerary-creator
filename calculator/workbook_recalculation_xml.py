"""Apply workbook recalculation metadata without touching other XML."""

from __future__ import annotations

import re
from typing import Mapping


def patch_workbook_calculation_properties(
    xml: str,
    properties: Mapping[str, object],
) -> str:
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
