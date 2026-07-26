"""Immutable Local Library workbook contracts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from calculator.library_model import LocalLibraryRow


@dataclass(frozen=True)
class LocalLibraryDiagnostic:
    """One actionable non-fatal Local Library workbook issue."""

    category: str
    code: str
    message: str
    worksheet: str = ""
    excel_row: int | None = None
    field: str = ""
    value: str = ""


class LocalLibraryWorkbookError(RuntimeError):
    """Raised when the bundled Local Library workbook is unusable."""

    def __init__(
        self,
        message: str,
        *,
        category: str = "fatal_workbook",
        code: str = "workbook_unusable",
        diagnostics: tuple[LocalLibraryDiagnostic, ...] = (),
    ) -> None:
        super().__init__(message)
        self.category = category
        self.code = code
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class LocalLibraryWorkbook:
    rows: tuple[LocalLibraryRow, ...]
    currency_rates: Mapping[str, float]
    path: Path
    fingerprint: str
    diagnostics: tuple[LocalLibraryDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))
        object.__setattr__(self, "currency_rates", MappingProxyType(dict(self.currency_rates)))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    @property
    def invalid_records(self) -> tuple[LocalLibraryDiagnostic, ...]:
        return tuple(issue for issue in self.diagnostics if issue.category == "invalid_record")

    @property
    def warnings(self) -> tuple[LocalLibraryDiagnostic, ...]:
        return tuple(issue for issue in self.diagnostics if issue.category == "warning")


@dataclass(frozen=True)
class FormulaCell:
    column_index: int
    formula: str
    cached_value: str | None
    cached_error: bool
