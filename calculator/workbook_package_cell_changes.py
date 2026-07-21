"""Translate canonical workbook export cells into package-level changes."""

from __future__ import annotations

from dataclasses import dataclass
import re

from calculator.workbook_export_plan import CellValueKind, ExportCell

_CELL_REFERENCE_RE = re.compile(r"[A-Z]+\d+")


@dataclass(frozen=True)
class PackageCellChange:
    """One validated worksheet-cell mutation for the XML renderer."""

    value: object
    kind: CellValueKind


def generate_cell_changes(cells: tuple[ExportCell, ...]) -> dict[str, PackageCellChange]:
    """Return validated, duplicate-free package changes keyed by cell reference."""

    changes: dict[str, PackageCellChange] = {}
    for cell in cells:
        reference = cell.reference
        if not _CELL_REFERENCE_RE.fullmatch(reference):
            raise ValueError(f"Invalid export cell reference: {reference}")
        if reference in changes:
            raise ValueError(f"Duplicate export cell reference: {reference}")
        changes[reference] = PackageCellChange(value=cell.value, kind=cell.kind)
    return changes
