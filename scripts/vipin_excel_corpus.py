"""Regression runner for messy Nordic calculator Excel workbooks.

The app does not depend on this module at runtime.  It is a developer tool used
for large real-world parser/generator corpus checks from supplier calculator
workbooks.  It intentionally uses only the Python standard library for XLSX
extraction so it can run in CI/dev shells without Excel, LibreOffice, pandas, or
openpyxl.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

_HEADER_ALIASES = {
    "day": {"day"},
    "type": {"type"},
    "city": {"city", "city / area", "location", "destination"},
    "element": {"travel element", "details", "activity", "description"},
    "nights": {"no of night", "no of nights", "nights"},
    "from_date": {"from date", "date"},
    "to_date": {"to date"},
    "supplier": {"supplier"},
}

_NON_ITINERARY_TYPES = {
    "",
    "per pax",
    "one pax",
    "two pax",
    "three pax",
    "four pax",
    "five pax",
    "six pax",
    "price",
    "cost",
    "total",
    "margin",
    "markup",
}

_ALLOWED_EMPTY_TITLE_TYPES = {"Arrival", "Departure", "Leisure"}
_TITLE_PROSE_MARKERS = re.compile(
    r"\b(overview|what'?s included|what is included|meeting point|pick[- ]?up / meeting|pick[- ]?up point|"
    r"end point|notable sights|highlights:|duration:|includes?:|important information|please note|"
    r"the full arctic expedition|professional[, ]+english[- ]speaking|client will|you will)\b",
    flags=re.IGNORECASE,
)
_DAY_RE = re.compile(r"\bday\s*\d+\b", flags=re.IGNORECASE)
_DATEISH_RE = re.compile(r"\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?|\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class ExcelCorpusItem:
    file: str
    sheet: str
    row: int
    day: str
    row_type: str
    city: str
    element: str
    nights: str = ""
    from_date: str = ""
    to_date: str = ""
    supplier: str = ""

    @property
    def source_id(self) -> str:
        return f"{self.file}::{self.sheet}::R{self.row}"

    def as_raw_line(self) -> str:
        values = [
            "",
            self.day,
            self.row_type,
            self.nights,
            self.from_date,
            self.to_date,
            "",
            "",
            self.supplier,
            self.city,
            self.element,
        ]
        return "\t".join(str(value or "") for value in values)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExcelCorpusItem":
        return cls(
            file=str(data.get("file", "") or ""),
            sheet=str(data.get("sheet", "") or ""),
            row=int(data.get("row", 0) or 0),
            day=str(data.get("day", "") or ""),
            row_type=str(data.get("row_type", "") or ""),
            city=str(data.get("city", "") or ""),
            element=str(data.get("element", "") or ""),
            nights=str(data.get("nights", "") or ""),
            from_date=str(data.get("from_date", "") or ""),
            to_date=str(data.get("to_date", "") or ""),
            supplier=str(data.get("supplier", "") or ""),
        )


@dataclass(frozen=True)
class BadOutput:
    source_id: str
    category: str
    reason: str
    source_type: str
    source_day: str
    source_city: str
    source_date: str
    parsed_type: str = ""
    effective_type: str = ""
    parsed_city: str = ""
    parsed_title: str = ""
    generated_title: str = ""
    confidence: int | None = None
    flags: tuple[str, ...] = ()
    details_excerpt: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["flags"] = list(self.flags)
        return data


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm_key(value: Any) -> str:
    return _norm(value).lower()


def _col_to_idx(ref: str) -> int:
    match = re.match(r"([A-Z]+)", ref or "")
    if not match:
        return 0
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - 64
    return value


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    strings: list[str] = []
    with zf.open("xl/sharedStrings.xml") as handle:
        for _event, elem in ET.iterparse(handle, events=("end",)):
            if elem.tag == MAIN_NS + "si":
                strings.append("".join(text.text or "" for text in elem.iter(MAIN_NS + "t")))
                elem.clear()
    return strings


def _workbook_sheets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("pr:Relationship", rel_ns)}
    sheets: list[tuple[str, str]] = []
    sheets_el = workbook.find("a:sheets", ns)
    if sheets_el is None:
        return []
    for sheet in sheets_el:
        name = sheet.attrib.get("name", "Sheet")
        target = rel_map.get(sheet.attrib.get(REL_NS, ""), "")
        if target and not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        if target:
            sheets.append((name, target))
    return sheets


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        value = cell.find(MAIN_NS + "v")
        if value is None or value.text is None:
            return ""
        try:
            return shared_strings[int(value.text)]
        except (ValueError, IndexError):
            return value.text or ""
    if cell_type == "inlineStr":
        inline = cell.find(MAIN_NS + "is")
        return "" if inline is None else "".join(text.text or "" for text in inline.iter(MAIN_NS + "t"))
    value = cell.find(MAIN_NS + "v")
    return "" if value is None else (value.text or "")


def _parse_rows(
    zf: zipfile.ZipFile,
    target: str,
    shared_strings: list[str],
    *,
    max_rows: int = 130,
    max_cols: int = 25,
) -> dict[int, dict[int, str]]:
    rows: dict[int, dict[int, str]] = defaultdict(dict)
    with zf.open(target) as handle:
        for _event, row in ET.iterparse(handle, events=("end",)):
            if row.tag != MAIN_NS + "row":
                continue
            row_index = int(row.attrib.get("r", "0") or 0)
            if row_index > max_rows:
                break
            for cell in row.findall(MAIN_NS + "c"):
                col = _col_to_idx(cell.attrib.get("r", ""))
                if not col or col > max_cols:
                    continue
                value = _norm(_cell_value(cell, shared_strings))
                if value:
                    rows[row_index][col] = value
            row.clear()
    return rows


def _find_header_rows(rows: Mapping[int, Mapping[int, str]]) -> list[tuple[int, int, dict[int, str]]]:
    candidates: list[tuple[int, int, dict[int, str]]] = []
    for row_index, cols in rows.items():
        labels = {col: _norm_key(value) for col, value in cols.items()}
        values = list(labels.values())
        score = 0
        if any(value == "day" for value in values):
            score += 2
        if any(value == "type" for value in values):
            score += 2
        if any(value in _HEADER_ALIASES["city"] for value in values):
            score += 1
        if any(value in _HEADER_ALIASES["element"] for value in values):
            score += 2
        if any(value in (_HEADER_ALIASES["from_date"] | _HEADER_ALIASES["to_date"] | _HEADER_ALIASES["nights"]) for value in values):
            score += 1
        if score >= 4:
            candidates.append((row_index, score, labels))
    return sorted(candidates, key=lambda item: (-item[1], item[0]))


def _map_headers(labels: Mapping[int, str]) -> dict[str, int]:
    mapped: dict[str, int] = {}
    for col, value in labels.items():
        for key, aliases in _HEADER_ALIASES.items():
            if value in aliases:
                mapped.setdefault(key, col)
                break
    return mapped


def _looks_itinerary_like(day: str, row_type: str, element: str, city: str) -> bool:
    # Match the historical corpus extraction contract: keep every row that
    # belongs to a Day block or has a Type value.  Cost/calculator rows are
    # intentionally retained so the parser can prove they are skipped safely.
    if not any([day, row_type, element, city]):
        return False
    return bool(_DAY_RE.search(day) or row_type)


def collect_excel_corpus_items(paths: Iterable[str | Path]) -> list[ExcelCorpusItem]:
    """Extract itinerary-like calculator rows from the supplied workbook paths."""

    items: list[ExcelCorpusItem] = []
    for path_value in paths:
        path = Path(path_value)
        with zipfile.ZipFile(path) as zf:
            shared_strings = _load_shared_strings(zf)
            for sheet_name, target in _workbook_sheets(zf):
                rows = _parse_rows(zf, target, shared_strings)
                header_rows = _find_header_rows(rows)
                if not header_rows:
                    continue
                header_row, _score, labels = header_rows[0]
                headers = _map_headers(labels)
                if "day" not in headers or "type" not in headers:
                    continue
                for row_number in sorted(rows):
                    if row_number <= header_row:
                        continue
                    values = rows[row_number]
                    day = _norm(values.get(headers.get("day", -1), ""))
                    row_type = _norm(values.get(headers.get("type", -1), ""))
                    city = _norm(values.get(headers.get("city", -1), "")) if "city" in headers else ""
                    element = _norm(values.get(headers.get("element", -1), "")) if "element" in headers else ""
                    if not _looks_itinerary_like(day, row_type, element, city):
                        continue
                    items.append(ExcelCorpusItem(
                        file=path.name,
                        sheet=sheet_name,
                        row=row_number,
                        day=day,
                        row_type=row_type,
                        city=city,
                        element=element,
                        nights=_norm(values.get(headers.get("nights", -1), "")) if "nights" in headers else "",
                        from_date=_norm(values.get(headers.get("from_date", -1), "")) if "from_date" in headers else "",
                        to_date=_norm(values.get(headers.get("to_date", -1), "")) if "to_date" in headers else "",
                        supplier=_norm(values.get(headers.get("supplier", -1), "")) if "supplier" in headers else "",
                    ))
    return items


def _source_missing_categories(item: ExcelCorpusItem) -> list[BadOutput]:
    categories: list[BadOutput] = []
    if not item.day:
        categories.append(_bad(item, "missing_source_day", "Source row has no day value."))
    if not item.row_type:
        categories.append(_bad(item, "missing_source_type", "Source row has no type value."))
    elif _norm_key(item.row_type) in _NON_ITINERARY_TYPES:
        categories.append(_bad(item, "non_itinerary_type", "Source row type looks like a calculator/cost row."))
    if not item.city:
        categories.append(_bad(item, "missing_source_city", "Source row has no city/area value."))
    if not (item.from_date or item.to_date or _DATEISH_RE.search(item.element)):
        categories.append(_bad(item, "missing_source_date", "Source row has no date value."))
    return categories


def _bad(item: ExcelCorpusItem, category: str, reason: str, row: Mapping[str, Any] | None = None, generated_title: str = "") -> BadOutput:
    row = row or {}
    return BadOutput(
        source_id=item.source_id,
        category=category,
        reason=reason,
        source_type=item.row_type,
        source_day=item.day,
        source_city=item.city,
        source_date=item.from_date or item.to_date,
        parsed_type=str(row.get("type", "") or ""),
        effective_type=str(row.get("effective_type", "") or ""),
        parsed_city=str(row.get("city", "") or ""),
        parsed_title=str(row.get("title", "") or ""),
        generated_title=generated_title,
        confidence=int(row.get("parser_confidence")) if str(row.get("parser_confidence", "")).isdigit() else None,
        flags=tuple(str(flag) for flag in (row.get("parser_review_flags") or [])),
        details_excerpt=_norm(str(row.get("details", "") or item.element))[:280],
    )


def _looks_like_activity_prose_title(title: str) -> bool:
    title = _norm(title)
    if not title:
        return False
    if _TITLE_PROSE_MARKERS.search(title):
        return True
    if len(title) >= 120 and re.search(r"[.!?]", title):
        return True
    if len(title.split()) >= 18 and re.search(r"\b(and|with|including|where|while|before|after)\b", title, flags=re.IGNORECASE):
        return True
    return False


def _row_output_categories(item: ExcelCorpusItem, row: Mapping[str, Any], generated_title: str = "") -> list[BadOutput]:
    categories: list[BadOutput] = []
    row_type = str(row.get("effective_type") or row.get("type") or "")
    title = _norm(row.get("title", ""))
    output_title = _norm(generated_title or title)
    city = _norm(row.get("city", ""))
    flags = set(row.get("parser_review_flags") or [])

    if not title and row_type not in _ALLOWED_EMPTY_TITLE_TYPES:
        categories.append(_bad(item, "blank_title", "Parsed row has a blank title.", row, output_title))
    if len(title) > 100:
        categories.append(_bad(item, "overlong_title", "Parsed title is over 100 characters.", row, output_title))
    if _looks_like_activity_prose_title(title):
        categories.append(_bad(item, "activity_text_used_as_title", "Parsed title looks like supplier prose or activity body text.", row, output_title))
    if output_title and output_title != title:
        if len(output_title) > 100:
            categories.append(_bad(item, "overlong_generated_title", "Generated editable title is over 100 characters.", row, output_title))
        if _looks_like_activity_prose_title(output_title):
            categories.append(_bad(item, "activity_text_used_as_generated_title", "Generated editable title looks like supplier prose.", row, output_title))
    if row_type in {"Hotel", "Activity", "Transfer", "Transport", "Train", "Flight", "Cruise", "Ferry"} and not city and "missing_city" in flags:
        categories.append(_bad(item, "missing_parsed_city", "Parsed row is missing city/area.", row, output_title))
    if not row.get("type"):
        categories.append(_bad(item, "missing_parsed_type", "Parsed row is missing type.", row, output_title))
    if "missing_activity_title" in flags:
        categories.append(_bad(item, "missing_activity_title", "Parser flagged missing activity title.", row, output_title))
    return categories



def _generated_titles_for_rows(rows: list[Mapping[str, Any]]) -> dict[str, str]:
    """Return editable output titles for parsed rows.

    The UI output state seeds row titles from the parsed title for non-activity
    rows and from activity-title cleanup for activity rows.  For the large Excel
    corpus, the parser title is the title-safety contract under test; full day
    intro generation is intentionally avoided because the workbooks are hundreds
    of unrelated quote sheets, not one itinerary.
    """

    return {str(row.get("row_id") or ""): str(row.get("title", "") or "") for row in rows if row.get("row_id")}


def _worker_parse_chunk(payload: tuple[int, list[ExcelCorpusItem]]) -> list[tuple[ExcelCorpusItem, dict[str, Any]]]:
    """Parse one independent workbook chunk in a worker process."""

    _start, chunk = payload
    import diagnostics
    from itinerary_parser import parse_itinerary

    diagnostics.reset()
    rows = parse_itinerary("\n".join(item.as_raw_line() for item in chunk))
    parsed: list[tuple[ExcelCorpusItem, dict[str, Any]]] = []
    for row in rows:
        line_number = int(row.get("line_number") or 0)
        if 0 < line_number <= len(chunk):
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
        # Use small, restarted process pools instead of one long-lived pool.
        # The real Excel corpus contains many high-cardinality supplier strings;
        # restarting workers every few hundred chunks keeps caches and regex state
        # bounded and makes the full-corpus check reliably finish locally.
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


def evaluate_excel_corpus(
    items: Iterable[ExcelCorpusItem],
    *,
    workers: int = 1,
    progress: bool = False,
    chunk_size: int = 5,
) -> dict[str, Any]:
    """Parse and generate editable titles for every extracted corpus row."""

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
        if _norm_key(item.row_type) not in _NON_ITINERARY_TYPES:
            bad_outputs.append(_bad(item, "unexpected_skip", "Parser returned no row for this itinerary-like source row."))

    bulk_generation_ok = False
    bulk_error = ""
    try:
        # The generator path is intentionally exercised in chunks: these workbooks
        # contain hundreds of unrelated calculator sheets, not one continuous tour.
        # Chunking avoids false duplicate suppression across separate quotes while
        # still running every row through editable title generation.
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

def load_items_jsonl(path: str | Path) -> list[ExcelCorpusItem]:
    """Load pre-extracted corpus rows from a JSONL fixture.

    This keeps the full real-world calculator corpus available for regression
    checks without committing large binary Excel workbooks to the repo.
    """

    input_path = Path(path)
    items: list[ExcelCorpusItem] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid corpus JSONL at {input_path}:{line_number}: {exc}") from exc
            items.append(ExcelCorpusItem.from_dict(payload))
    return items


def write_items_jsonl(items: Iterable[ExcelCorpusItem], path: str | Path) -> None:
    """Write extracted corpus rows as a stable JSONL fixture."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(item.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def write_bad_outputs_jsonl(bad_outputs: Iterable[BadOutput], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for bad_output in bad_outputs:
            handle.write(json.dumps(bad_output.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def write_markdown_report(
    summary: Mapping[str, Any],
    path: str | Path,
    *,
    bad_jsonl_path: str | Path | None = None,
    report_label: str | None = None,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bad_outputs = list(summary.get("bad_outputs") or [])
    sample_by_category: dict[str, list[Any]] = defaultdict(list)
    priority = [
        "blank_title",
        "overlong_title",
        "activity_text_used_as_title",
        "activity_text_used_as_generated_title",
        "missing_parsed_city",
        "missing_activity_title",
        "unexpected_skip",
        "missing_source_type",
        "non_itinerary_type",
    ]
    for bad_output in bad_outputs:
        category = bad_output.category if isinstance(bad_output, BadOutput) else str(dict(bad_output).get("category", ""))
        if len(sample_by_category[category]) < 6:
            sample_by_category[category].append(bad_output)
    resolved_report_label = report_label or ("INPUT5" if "input5" in output_path.name.lower() else "INPUT4")
    lines = [
        f"# {resolved_report_label} Vipin Excel Corpus Regression Report",
        "",
        "Purpose: run the real messy Nordic calculator corpus through parser and editable-title generation, then log risky outputs for regression hardening.",
        "",
        "## Summary",
        "",
        f"- Corpus rows checked: {summary.get('item_count', 0)}",
        f"- Parsed output rows: {summary.get('parsed_count', 0)}",
        f"- Generated editable titles checked: {summary.get('generated_count', 0)}",
        f"- Workbooks: {len(summary.get('file_counts', {}))}",
        f"- Sheets with extracted rows: {summary.get('sheet_count', 0)}",
        f"- Parser exceptions: {summary.get('parse_errors', 0)}",
        f"- Rows skipped by parser: {summary.get('skipped_count', 0)}",
        f"- Average parser confidence: {summary.get('average_confidence', 0)}%",
        f"- Rows under 80 confidence: {summary.get('under_80_confidence_count', 0)}",
        f"- Whole-corpus generation smoke: {'passed' if summary.get('bulk_generation_ok') else 'failed'}",
    ]
    if summary.get("bulk_generation_error"):
        lines.append(f"- Whole-corpus generation error: `{summary.get('bulk_generation_error')}`")
    if bad_jsonl_path:
        lines.append(f"- Bad-output log: `{Path(bad_jsonl_path).as_posix()}`")
    lines.extend(["", "## Bad-output counts", ""])
    for category, count in (summary.get("bad_output_counts") or {}).items():
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Parser review flags", ""])
    for flag, count in (summary.get("parser_flag_counts") or {}).items():
        lines.append(f"- {flag}: {count}")
    lines.extend(["", "## Top source types", ""])
    for row_type, count in (summary.get("type_counts") or {}).items():
        lines.append(f"- {row_type or '[blank]'}: {count}")
    lines.extend(["", "## Worst-case samples", ""])
    categories = [category for category in priority if sample_by_category.get(category)]
    categories.extend(category for category in sample_by_category if category not in categories)
    if not categories:
        lines.append("No bad outputs detected by the configured heuristics.")
    else:
        for category in categories:
            lines.append(f"### {category}")
            for bad in sample_by_category[category]:
                data = bad.as_dict() if isinstance(bad, BadOutput) else dict(bad)
                lines.append(
                    f"- {data.get('source_id')} | "
                    f"type={data.get('source_type')!r} | title={data.get('parsed_title')!r} | "
                    f"generated={data.get('generated_title')!r} | reason={data.get('reason')}"
                )
            lines.append("")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Vipin Excel parser/generator corpus checks.")
    parser.add_argument("workbooks", nargs="*", help="XLSX workbook paths to scan")
    parser.add_argument("--items-jsonl", help="Read a pre-extracted ExcelCorpusItem JSONL fixture instead of scanning XLSX files.")
    parser.add_argument("--export-items-jsonl", help="Write extracted ExcelCorpusItem rows to this JSONL fixture path.")
    parser.add_argument("--report", default="docs/reports/input4_vipin_excel_corpus_report.md")
    parser.add_argument("--bad-jsonl", default="docs/reports/input4_vipin_excel_bad_outputs.jsonl")
    parser.add_argument("--report-label", default=None, help="Heading label for the markdown report, for example VIPIN_FULL.")
    parser.add_argument("--workers", type=int, default=1, help="Parallel parser workers. Use 4-8 for the full Vipin corpus.")
    parser.add_argument("--chunk-size", type=int, default=5, help="Parser rows per isolated chunk. Keep low for strict regression checks; raise for quick smoke runs.")
    parser.add_argument("--progress", action="store_true", help="Print progress to stderr while parsing chunks.")
    args = parser.parse_args(argv)

    if args.items_jsonl:
        if args.workbooks:
            parser.error("Pass either workbook paths or --items-jsonl, not both.")
        items = load_items_jsonl(args.items_jsonl)
    else:
        if not args.workbooks:
            parser.error("Pass one or more workbook paths, or use --items-jsonl.")
        items = collect_excel_corpus_items(args.workbooks)
    if args.export_items_jsonl:
        write_items_jsonl(items, args.export_items_jsonl)

    summary = evaluate_excel_corpus(items, workers=max(1, args.workers), progress=args.progress, chunk_size=max(1, args.chunk_size))
    write_bad_outputs_jsonl(summary["bad_outputs"], args.bad_jsonl)
    write_markdown_report(summary, args.report, bad_jsonl_path=args.bad_jsonl, report_label=args.report_label)
    print(json.dumps({key: value for key, value in summary.items() if key != "bad_outputs"}, indent=2, ensure_ascii=False))
    return 0 if summary["parse_errors"] == 0 and summary["bulk_generation_ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
