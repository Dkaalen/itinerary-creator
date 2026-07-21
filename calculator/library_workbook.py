"""Validated repository-local Excel Local Library loader."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from openpyxl import load_workbook

from calculator.library_model import LocalLibraryRow
from calculator.library_normalize import normalize_library_mapping

WORKBOOK_PATH = Path(__file__).resolve().parents[1] / "data" / "Calculation-template-Inputs-fixed-outline-restored.xlsx"
REQUIRED_SHEETS = ("Curr", "General", "Hotels", "Transfers", "Transport", "Activities")
DATA_SHEETS = REQUIRED_SHEETS[1:]
_REQUIRED_HEADERS = {"ID", "Type", "Travel element", "Gross P per unit", "Supp Comm", "Supp curr", "Sales P per unit", "Sales curr"}

class LocalLibraryWorkbookError(RuntimeError):
    """Raised when the bundled Local Library workbook is unusable."""

@dataclass(frozen=True)
class LocalLibraryWorkbook:
    rows: tuple[LocalLibraryRow, ...]
    currency_rates: Mapping[str, float]
    path: Path
    fingerprint: str

@lru_cache(maxsize=4)
def _load_cached(path_text: str, modified_ns: int, size: int) -> LocalLibraryWorkbook:
    path = Path(path_text)
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        raise LocalLibraryWorkbookError(f"Local Library workbook is corrupt or unreadable: {path.name}") from exc
    missing = [name for name in REQUIRED_SHEETS if name not in workbook.sheetnames]
    if missing:
        raise LocalLibraryWorkbookError(f"Local Library workbook is missing required sheet(s): {', '.join(missing)}")
    rates = _currency_rates(workbook["Curr"])
    rows: list[LocalLibraryRow] = []
    for sheet_name in DATA_SHEETS:
        sheet = workbook[sheet_name]
        headers, header_row = _headers(sheet)
        missing_headers = sorted(_REQUIRED_HEADERS - set(headers))
        if missing_headers:
            raise LocalLibraryWorkbookError(f"{sheet_name} is missing required header(s): {', '.join(missing_headers)}")
        for source_row, values in enumerate(sheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
            mapping = {header: value for header, value in zip(headers, values) if header}
            if not _has_product_content(mapping):
                continue
            enriched = dict(mapping)
            enriched.update({
                "schema_version": "local_library_v1",
                "source_workbook": path.name,
                "source_sheet": sheet_name,
                "source_row": source_row,
                "country": str(mapping.get("ID") or "").strip(),
                "category": sheet_name,
                "record_type": "line",
                "is_deleted": False,
                "is_fetchable": True,
            })
            row = normalize_library_mapping(enriched)
            _validate_row(row, sheet_name, source_row, rates)
            rows.append(row)
    if not rows:
        raise LocalLibraryWorkbookError("Local Library workbook contains no fetchable rows.")
    fingerprint = f"{modified_ns:x}-{size:x}"
    return LocalLibraryWorkbook(tuple(rows), rates, path, fingerprint)

def load_local_library_workbook(path: str | Path = WORKBOOK_PATH) -> LocalLibraryWorkbook:
    workbook_path = Path(path)
    if not workbook_path.is_file():
        raise LocalLibraryWorkbookError(f"Local Library workbook is missing: {workbook_path}")
    stat = workbook_path.stat()
    return _load_cached(str(workbook_path.resolve()), stat.st_mtime_ns, stat.st_size)

def clear_local_library_workbook_cache() -> None:
    _load_cached.cache_clear()

def _headers(sheet) -> tuple[tuple[str, ...], int]:
    for row_number, row in enumerate(sheet.iter_rows(min_row=1, max_row=12, values_only=True), start=1):
        headers = tuple(str(value).strip() if value is not None else "" for value in row)
        if "Travel element" in headers and "Type" in headers:
            return headers, row_number
    raise LocalLibraryWorkbookError(f"{sheet.title} has no recognizable Calculator header row.")

def _currency_rates(sheet) -> dict[str, float]:
    rates = {"NOK": 1.0}
    for row in sheet.iter_rows(values_only=True):
        code = str(row[1] or "").strip().upper() if len(row) > 1 else ""
        value = row[2] if len(row) > 2 else None
        if not code:
            continue
        try:
            rate = float(value)
        except (TypeError, ValueError):
            raise LocalLibraryWorkbookError(f"Curr contains an invalid rate for {code}.")
        if rate <= 0:
            raise LocalLibraryWorkbookError(f"Curr contains a non-positive rate for {code}.")
        rates[code] = rate
    if len(rates) < 2:
        raise LocalLibraryWorkbookError("Curr contains no usable currency rates.")
    return rates

def _has_product_content(mapping: Mapping[str, object]) -> bool:
    return bool(str(mapping.get("Travel element") or "").strip() or str(mapping.get("Type") or "").strip())

def _validate_row(row: LocalLibraryRow, sheet: str, source_row: int, rates: Mapping[str, float]) -> None:
    for code in (row.supplier_currency, row.sales_currency):
        if code and code not in rates:
            raise LocalLibraryWorkbookError(f"{sheet} row {source_row} uses unsupported currency {code}.")
