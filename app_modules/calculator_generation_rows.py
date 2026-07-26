"""Preserve Calculator Local Library provenance through generation parsing."""
from __future__ import annotations

from collections.abc import Iterable

from calculator.library_identity import local_library_source_identity
from calculator.row_model import CalculatorRow
from calculator.to_itinerary_input import calculator_rows_to_raw_lines
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


def calculator_rows_have_library_provenance(rows: Iterable[CalculatorRow]) -> bool:
    return any(bool(row.library_id and row.source_sheet and row.source_row is not None) for row in rows)


def parse_and_normalize_calculator_rows(rows: Iterable[CalculatorRow]) -> list[dict]:
    """Parse Calculator rows while retaining distinct workbook source identity.

    Rows are parsed one source line at a time only for the Calculator provenance
    path. This prevents two intentionally identical workbook products from
    being collapsed by content-based parser duplicate protection.
    """

    parsed_rows: list[dict] = []
    for calculator_row, raw_line in calculator_rows_to_raw_lines(rows):
        source_rows = parse_itinerary(raw_line)
        for parsed in source_rows:
            enriched = dict(parsed)
            _attach_calculator_provenance(enriched, calculator_row)
            parsed_rows.append(enriched)
    return normalize_itinerary_rows(parsed_rows)


def _attach_calculator_provenance(parsed: dict, row: CalculatorRow) -> None:
    parsed["calculator_row_id"] = str(row.row_id or "")
    if not (row.library_id and row.source_sheet and row.source_row is not None):
        return
    provenance = {
        "source_workbook": row.source_workbook,
        "source_sheet": row.source_sheet,
        "source_row": row.source_row,
    }
    parsed.update(
        {
            "library_id": row.library_id,
            **provenance,
            "library_source_identity": local_library_source_identity(provenance),
            "source_url": row.url,
            "row_id": f"library-{row.library_id}-calculator-{row.row_id}",
        }
    )


__all__ = ["calculator_rows_have_library_provenance", "parse_and_normalize_calculator_rows"]
