"""Read-only queries over canonical editor page contracts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from itinerary_generation.editor_contract_ids import final_section_page_id


def hidden_page_ids(document_pages: Any) -> set[str]:
    if not isinstance(document_pages, (list, tuple)): return set()
    return {str(page.get("page_id") or "").strip() for page in document_pages if isinstance(page, Mapping) and page.get("page_id") and bool(page.get("is_hidden"))}


def document_pages_from_draft(editor_draft: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if not isinstance(editor_draft, Mapping) or not isinstance(editor_draft.get("document_pages"), (list, tuple)): return []
    return [page for page in editor_draft["document_pages"] if isinstance(page, Mapping)]


def page_is_hidden(hidden_ids: set[str] | frozenset[str] | Sequence[str] | None, page_id: str) -> bool:
    return str(page_id or "") in {str(item) for item in (hidden_ids or set())}


def final_section_is_hidden(hidden_ids: set[str] | frozenset[str] | Sequence[str] | None, section_id: str) -> bool:
    return page_is_hidden(hidden_ids, final_section_page_id(section_id))


def page_order_from_document_pages(document_pages: Any) -> list[str]:
    if not isinstance(document_pages, (list, tuple)): return []
    ordered: list[tuple[float, str]] = []
    for index, page in enumerate(document_pages):
        if not isinstance(page, Mapping): continue
        page_id = str(page.get("page_id") or "").strip()
        if not page_id: continue
        try: order = float(page.get("sort_order") or index + 1)
        except (TypeError, ValueError): order = float(index + 1)
        ordered.append((order, page_id))
    return [page_id for _, page_id in sorted(ordered, key=lambda item: item[0])]


def page_order_from_draft(editor_draft: Mapping[str, Any] | None) -> list[str]:
    return page_order_from_document_pages(document_pages_from_draft(editor_draft))


def ordered_page_ids(default_ids: Sequence[str], requested_order: Sequence[str] | None) -> list[str]:
    defaults = [str(page_id) for page_id in default_ids if str(page_id or "").strip()]
    ordered = [str(page_id) for page_id in (requested_order or []) if str(page_id) in defaults]
    ordered.extend(page_id for page_id in defaults if page_id not in ordered)
    return ordered


def manual_pages_from_document_pages(document_pages: Any, hidden_ids: set[str] | frozenset[str] | Sequence[str] | None = None) -> list[dict[str, Any]]:
    hidden = {str(item) for item in (hidden_ids or hidden_page_ids(document_pages))}
    pages: list[dict[str, Any]] = []
    if not isinstance(document_pages, (list, tuple)): return pages
    for page in document_pages:
        if not isinstance(page, Mapping) or page.get("page_type") != "manual": continue
        page_id = str(page.get("page_id") or "").strip()
        if page_id in hidden: continue
        parts: list[str] = []
        for block in page.get("manual_blocks") if isinstance(page.get("manual_blocks"), (list, tuple)) else []:
            fields = block.get("editable_fields") if isinstance(block, Mapping) and isinstance(block.get("editable_fields"), Mapping) else {}
            html = str(fields.get("content_html") or "").strip()
            if html: parts.append(html)
        pages.append({"page_id": page_id, "title": str(page.get("title") or "Custom page").strip() or "Custom page", "content_html": "".join(parts), "sort_order": int(page.get("sort_order") or 0)})
    return sorted(pages, key=lambda page: int(page.get("sort_order") or 0))


def manual_pages_from_draft(editor_draft: Mapping[str, Any] | None, hidden_ids: set[str] | frozenset[str] | Sequence[str] | None = None) -> list[dict[str, Any]]:
    return manual_pages_from_document_pages(document_pages_from_draft(editor_draft), hidden_ids)
