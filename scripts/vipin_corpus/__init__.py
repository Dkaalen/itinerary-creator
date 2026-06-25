"""Responsibility-split Vipin Excel corpus runner package."""

from scripts.vipin_corpus.bad_outputs import (
    _bad,
    _has_usable_source_content,
    _looks_like_activity_prose_title,
    _looks_report_only_source,
    _row_output_categories,
    _source_missing_categories,
)
from scripts.vipin_corpus.constants import (
    ALLOWED_EMPTY_TITLE_TYPES as _ALLOWED_EMPTY_TITLE_TYPES,
    DATEISH_RE as _DATEISH_RE,
    DAY_RE as _DAY_RE,
    HEADER_ALIASES as _HEADER_ALIASES,
    MAIN_NS,
    NON_ITINERARY_TYPES as _NON_ITINERARY_TYPES,
    REL_NS,
    TITLE_PROSE_MARKERS as _TITLE_PROSE_MARKERS,
)
from scripts.vipin_corpus.evaluate import evaluate_excel_corpus
from scripts.vipin_corpus.extract import (
    _cell_value,
    _col_to_idx,
    _find_header_rows,
    _load_shared_strings,
    _looks_itinerary_like,
    _map_headers,
    _parse_rows,
    _workbook_sheets,
    collect_excel_corpus_items,
)
from scripts.vipin_corpus.io import load_items_jsonl, write_bad_outputs_jsonl, write_items_jsonl
from scripts.vipin_corpus.models import BadOutput, ExcelCorpusItem
from scripts.vipin_corpus.parser_runner import _generated_titles_for_rows, _parse_rows_chunked, _worker_parse_chunk
from scripts.vipin_corpus.report import write_markdown_report
from scripts.vipin_corpus.text import _norm, _norm_key, _number_like

__all__ = [name for name in globals() if not name.startswith("__")]
