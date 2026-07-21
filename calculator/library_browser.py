"""Pure filtering and pagination helpers for the read-only Local Library browser."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from calculator.library_model import LocalLibraryRow


@dataclass(frozen=True)
class LocalLibraryBrowserFilters:
    """Exact browser filters plus an optional free-text query."""

    worksheet: str = ""
    country: str = ""
    city: str = ""
    row_type: str = ""
    supplier: str = ""
    currency: str = ""
    query: str = ""


@dataclass(frozen=True)
class LocalLibraryBrowserPage:
    """One bounded page of filtered Local Library rows."""

    rows: tuple[LocalLibraryRow, ...]
    total_rows: int
    page_number: int
    page_size: int
    page_count: int


def local_library_city(row: LocalLibraryRow) -> str:
    """Return the deterministic destination prefix from ``Travel element``."""

    prefix, separator, _ = str(row.travel_element or "").partition(":")
    return prefix.strip() if separator else ""


def local_library_filter_options(rows: tuple[LocalLibraryRow, ...]) -> dict[str, tuple[str, ...]]:
    """Return stable, case-insensitive option lists for browser filters."""

    active_rows = tuple(row for row in rows if not row.is_deleted)
    return {
        "worksheet": _unique_sorted(row.source_sheet for row in active_rows),
        "country": _unique_sorted(row.country for row in active_rows),
        "city": _unique_sorted(local_library_city(row) for row in active_rows),
        "row_type": _unique_sorted(row.type for row in active_rows),
        "supplier": _unique_sorted(row.supplier for row in active_rows),
        "currency": _unique_sorted(
            code
            for row in active_rows
            for code in (row.supplier_currency, row.sales_currency)
        ),
    }


def filter_local_library_rows(
    rows: tuple[LocalLibraryRow, ...],
    filters: LocalLibraryBrowserFilters,
) -> tuple[LocalLibraryRow, ...]:
    """Return active rows matching every selected browser filter."""

    query = _normalized(filters.query)
    matched = []
    for row in rows:
        if row.is_deleted:
            continue
        if not _same_or_blank(row.source_sheet, filters.worksheet):
            continue
        if not _same_or_blank(row.country, filters.country):
            continue
        if not _same_or_blank(local_library_city(row), filters.city):
            continue
        if not _same_or_blank(row.type, filters.row_type):
            continue
        if not _same_or_blank(row.supplier, filters.supplier):
            continue
        if filters.currency and _normalized(filters.currency) not in {
            _normalized(row.supplier_currency),
            _normalized(row.sales_currency),
        }:
            continue
        if query and query not in _search_haystack(row):
            continue
        matched.append(row)
    return tuple(matched)


def paginate_local_library_rows(
    rows: tuple[LocalLibraryRow, ...],
    *,
    page_number: int,
    page_size: int,
) -> LocalLibraryBrowserPage:
    """Return one clamped page without exposing an unbounded result set."""

    safe_size = max(1, int(page_size))
    page_count = max(1, ceil(len(rows) / safe_size))
    safe_page = min(max(1, int(page_number)), page_count)
    start = (safe_page - 1) * safe_size
    return LocalLibraryBrowserPage(
        rows=rows[start : start + safe_size],
        total_rows=len(rows),
        page_number=safe_page,
        page_size=safe_size,
        page_count=page_count,
    )


def _search_haystack(row: LocalLibraryRow) -> str:
    values = (
        row.source_sheet,
        row.country,
        local_library_city(row),
        row.category,
        row.type,
        row.supplier,
        row.travel_element,
        row.comments,
        row.url,
        row.library_id,
    )
    return _normalized(" | ".join(str(value or "") for value in values))


def _same_or_blank(value: object, selected: object) -> bool:
    return not _normalized(selected) or _normalized(value) == _normalized(selected)


def _unique_sorted(values: object) -> tuple[str, ...]:
    unique: dict[str, str] = {}
    for value in values:  # type: ignore[operator]
        text = str(value or "").strip()
        if text:
            unique.setdefault(_normalized(text), text)
    return tuple(sorted(unique.values(), key=lambda item: (_normalized(item), item)))


def _normalized(value: object) -> str:
    return " ".join(str(value or "").casefold().split())
