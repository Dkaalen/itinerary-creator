"""Source-row and stable-signature helpers for visual-editor payloads."""

import hashlib

from shared.source_rows import source_row_id, source_text


def _source_rows_payload(parsed_rows):
    """Return compact source-row details for the visual editor source panel."""

    rows = {}
    for index, row in enumerate(parsed_rows or []):
        if not isinstance(row, dict):
            continue
        row_id = source_row_id(row, index)
        rows[row_id] = {
            "row_id": row_id,
            "day": str(row.get("day") or ""),
            "date": str(row.get("date") or row.get("start_date") or ""),
            "type": str(row.get("effective_type") or row.get("type") or ""),
            "city": str(row.get("city") or row.get("destination") or ""),
            "title": str(row.get("title") or row.get("original_title") or row.get("hotel_name") or ""),
            "details": str(row.get("details") or row.get("description") or ""),
            "source_text": source_text(row, separator=" | ", limit=700),
        }
    return rows


def _generated_value_for_page_html(page):
    return str(page.get("html", "") if isinstance(page, dict) else page or "")


def _source_signature(parsed_rows, grouped_days):
    """Stable signature for the source itinerary behind the editor draft.

    Browser-local draft recovery is useful, but only while the editor is still
    looking at the same generated itinerary.  This signature prevents a stale
    localStorage draft from being merged into a different itinerary/project.
    """
    pieces = []
    rows = parsed_rows or []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        pieces.append("|".join([
            str(row.get("row_id") or row.get("line_number") or index),
            str(row.get("day") or ""),
            str(row.get("date") or row.get("start_date") or ""),
            str(row.get("type") or row.get("effective_type") or ""),
            str(row.get("city") or row.get("destination") or ""),
            str(row.get("title") or row.get("original_title") or ""),
            str(row.get("raw_text") or row.get("details") or ""),
        ]))
    if not pieces and grouped_days:
        for day, day_rows in grouped_days.items():
            pieces.append(str(day))
            for row in day_rows or []:
                pieces.append(str(row.get("row_id") or row.get("title") or row))
    payload = "\n".join(pieces)
    return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()[:20]


def _page_html_payload(page_htmls):
    pages = page_htmls if isinstance(page_htmls, list) else [page_htmls]
    return [
        {"html": str(page.get("html", "") if isinstance(page, dict) else page or "")}
        for page in pages
        if str(page.get("html", "") if isinstance(page, dict) else page or "").strip()
    ]
