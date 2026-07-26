"""Evaluate parsed/generated output quality for Vipin corpus items."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from scripts.vipin_corpus.bad_outputs import (
    _bad,
    _has_usable_source_content,
    _looks_report_only_source,
    _row_output_categories,
    _source_missing_categories,
)
from scripts.vipin_corpus.models import BadOutput, ExcelCorpusItem
from scripts.vipin_corpus.parser_runner import _generated_titles_for_rows, _parse_rows_chunked
from scripts.vipin_corpus.text import _norm_key


def evaluate_excel_corpus(
    items: Iterable[ExcelCorpusItem],
    *,
    workers: int = 1,
    progress: bool = False,
    chunk_size: int = 5,
) -> dict[str, Any]:
    """Parse, normalize, and inspect editable titles for extracted corpus rows."""

    item_list = list(items)
    bad_outputs: list[BadOutput] = []
    parse_errors = 0
    types = Counter(_norm_key(item.row_type) for item in item_list)
    files = Counter(item.file for item in item_list)
    sheets = {(item.file, item.sheet) for item in item_list}
    flags: Counter[str] = Counter()
    confidences: list[int] = []

    for item in item_list:
        bad_outputs.extend(_source_missing_categories(item))

    try:
        parsed_pairs = _parse_rows_chunked(item_list, workers=workers, progress=progress, chunk_size=chunk_size)
    except Exception as exc:  # pragma: no cover - exercised by real corpus runner
        parsed_pairs = []
        parse_errors += 1
        bad_outputs.append(BadOutput(
            source_id="whole_corpus",
            category="parse_exception",
            reason=f"Parser raised {exc.__class__.__name__}: {exc}",
            source_type="",
            source_day="",
            source_city="",
            source_date="",
        ))

    rows = [row for _item, row in parsed_pairs]
    generated_titles = _generated_titles_for_rows(rows)
    parsed_source_ids = {item.source_id for item, _row in parsed_pairs}
    for item, row in parsed_pairs:
        flags.update(str(flag) for flag in (row.get("parser_review_flags") or []))
        if str(row.get("parser_confidence", "")).isdigit():
            confidences.append(int(row["parser_confidence"]))
        generated_title = generated_titles.get(str(row.get("row_id") or ""), "")
        bad_outputs.extend(_row_output_categories(item, row, generated_title))

    for item in item_list:
        if item.source_id in parsed_source_ids:
            continue
        if not item.day or not item.row_type or _looks_report_only_source(item) or not _has_usable_source_content(item):
            continue
        bad_outputs.append(_bad(item, "unexpected_skip", "Parser returned no row for this itinerary-like source row."))

    bulk_generation_ok = False
    bulk_error = ""
    try:
        bulk_generation_ok = bool(rows and generated_titles)
    except Exception as exc:  # pragma: no cover - real runner guard
        bulk_error = f"{exc.__class__.__name__}: {exc}"

    return {
        "item_count": len(item_list),
        "parsed_count": len(rows),
        "generated_count": sum(1 for title in generated_titles.values() if title),
        "skipped_count": max(0, len(item_list) - len(parsed_source_ids)),
        "parse_errors": parse_errors,
        "file_counts": dict(sorted(files.items())),
        "sheet_count": len(sheets),
        "type_counts": dict(types.most_common(35)),
        "parser_flag_counts": dict(flags.most_common(35)),
        "average_confidence": round(sum(confidences) / len(confidences), 1) if confidences else 0,
        "under_80_confidence_count": sum(1 for confidence in confidences if confidence < 80),
        "bad_outputs": bad_outputs,
        "bad_output_counts": dict(Counter(item.category for item in bad_outputs).most_common()),
        "bulk_generation_ok": bulk_generation_ok,
        "bulk_generation_error": bulk_error,
    }
