"""Warning payload helpers for the visual editor."""

from itinerary_generation.transport_safety import scan_client_output


def _compact_model_warnings(structured_document, parsed_rows=None):
    warnings = []
    seen = set()
    row_lookup = {str(row.get("row_id") or ""): row for row in (parsed_rows or []) if isinstance(row, dict)}
    for warning in getattr(structured_document, "warnings", ()) or ():
        key = (warning.code, warning.message, tuple(warning.source_row_ids))
        if key in seen:
            continue
        seen.add(key)
        source_ids = list(warning.source_row_ids)
        source_row = next((row_lookup.get(str(row_id)) for row_id in source_ids if row_lookup.get(str(row_id))), None)
        page_label = ""
        if source_row:
            day = str(source_row.get("day") or "").strip()
            title = str(source_row.get("title") or source_row.get("original_title") or "").strip()
            city = str(source_row.get("city") or "").strip()
            bits = [bit for bit in (day, city, title) if bit]
            page_label = " · ".join(bits[:3])
        severity = str(warning.severity or "review").lower()
        warnings.append({
            "code": warning.code,
            "severity": "critical" if severity in {"critical", "error"} else "info" if severity == "info" else "review",
            "category": "model",
            "message": warning.message,
            "excerpt": warning.message,
            "page_label": page_label or "Structured itinerary",
            "source_row_ids": source_ids,
        })
    return warnings[:30]


def _client_output_warnings_for_payload(payload):
    """Return compact warning data for the inline editor warning panel."""
    pieces = []
    cover = payload.get("cover") or {}
    pieces.extend(str(cover.get(key, "")) for key in ("trip_title", "trip_subtitle", "trip_dates", "destinations_line"))
    for day in payload.get("days") or []:
        if isinstance(day, dict):
            pieces.extend(str(day.get(key, "")) for key in ("city", "title", "intro", "blocks_html"))
    final_pages = payload.get("final_pages") or {}
    pieces.extend(str(final_pages.get(key, "")) for key in ("whats_included_html", "whats_not_included_html", "whats_not_included_text", "important_travel_notes_text"))
    for page in final_pages.get("whats_included_pages_html") or []:
        if isinstance(page, dict):
            pieces.append(str(page.get("html", "")))
        else:
            pieces.append(str(page or ""))
    findings = scan_client_output("\n".join(piece for piece in pieces if piece))
    compact = []
    seen = set()
    for finding in findings:
        key = (finding.code, finding.excerpt)
        if key in seen:
            continue
        seen.add(key)
        compact.append({
            "code": finding.code,
            "severity": "review",
            "category": "client_output",
            "message": finding.excerpt,
            "excerpt": finding.excerpt,
        })
    return compact[:20]
