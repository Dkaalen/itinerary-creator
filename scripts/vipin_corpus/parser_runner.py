"""Parser execution helpers for Vipin corpus chunks."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import sys
from typing import Any, Mapping

from scripts.vipin_corpus.bad_outputs import _has_usable_source_content, _looks_report_only_source
from scripts.vipin_corpus.models import ExcelCorpusItem


def _generated_titles_for_rows(rows: list[Mapping[str, Any]]) -> dict[str, str]:
    """Return editable output titles for parsed rows."""

    return {str(row.get("row_id") or ""): str(row.get("title", "") or "") for row in rows if row.get("row_id")}


def _worker_parse_chunk(payload: tuple[int, list[ExcelCorpusItem]]) -> list[tuple[ExcelCorpusItem, dict[str, Any]]]:
    """Parse one workbook chunk and recheck chunk-only duplicate skips."""

    _start, chunk = payload
    import diagnostics
    from itinerary_parser import parse_itinerary

    diagnostics.reset()
    rows = parse_itinerary("\n".join(item.as_raw_line() for item in chunk))
    parsed: list[tuple[ExcelCorpusItem, dict[str, Any]]] = []
    represented_line_numbers: set[int] = set()
    for row in rows:
        line_number = int(row.get("line_number") or 0)
        if 0 < line_number <= len(chunk):
            represented_line_numbers.add(line_number)
            parsed.append((chunk[line_number - 1], row))
        else:
            parsed.append((ExcelCorpusItem(
                file="unknown",
                sheet="unknown",
                row=line_number,
                day=str(row.get("day", "")),
                row_type=str(row.get("type", "")),
                city=str(row.get("city", "")),
                element=str(row.get("details", "")),
            ), row))

    for line_number, item in enumerate(chunk, start=1):
        if line_number in represented_line_numbers:
            continue
        if _looks_report_only_source(item) or not _has_usable_source_content(item):
            continue
        retry_rows = parse_itinerary(item.as_raw_line())
        for retry_row in retry_rows:
            parsed.append((item, retry_row))

    return parsed


def _parse_rows_chunked(
    items: list[ExcelCorpusItem],
    *,
    chunk_size: int = 5,
    workers: int = 1,
    progress: bool = False,
) -> list[tuple[ExcelCorpusItem, dict[str, Any]]]:
    chunk_size = max(1, int(chunk_size or 5))
    chunks = [(start, items[start:start + chunk_size]) for start in range(0, len(items), chunk_size)]
    parsed: list[tuple[ExcelCorpusItem, dict[str, Any]]] = []

    if workers <= 1:
        for index, payload in enumerate(chunks, start=1):
            if progress and index % 100 == 0:
                print(f"parsed chunks: {index}/{len(chunks)}", file=sys.stderr, flush=True)
            parsed.extend(_worker_parse_chunk(payload))
    else:
        map_chunksize = max(1, min(16, len(chunks) // max(1, workers * 8) or 1))
        batch_size = max(100, workers * 60)
        completed = 0
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start:batch_start + batch_size]
            with ProcessPoolExecutor(max_workers=workers) as executor:
                for result in executor.map(_worker_parse_chunk, batch, chunksize=map_chunksize):
                    parsed.extend(result)
                    completed += 1
                    if progress and completed % 100 == 0:
                        print(f"parsed chunks: {completed}/{len(chunks)}", file=sys.stderr, flush=True)

    return sorted(parsed, key=lambda pair: (pair[0].file, pair[0].sheet, pair[0].row, str(pair[1].get("row_id", ""))))
