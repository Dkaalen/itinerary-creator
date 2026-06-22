"""Canonical editor page/block contract.

This is a foundation layer for the future document-style editor.  Existing
preview/PDF paths still consume the legacy day/final-page fields, but the visual
editor payload now also exposes stable pages and blocks for page navigation,
selection, delete/hide, add-page, duplicate and inspector workflows.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

PAGE_CONTRACT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class EditorBlockContract:
    block_id: str
    block_type: str
    title: str = ""
    editable_fields: dict[str, Any] = field(default_factory=dict)
    style_overrides: dict[str, Any] = field(default_factory=dict)
    image_binding: dict[str, Any] = field(default_factory=dict)
    source_row_ids: tuple[str, ...] = ()
    dirty_state: str = "clean"
    validation_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EditorPageContract:
    page_id: str
    page_type: str
    title: str
    source_day_id: str = ""
    source_section_id: str = ""
    source_row_ids: tuple[str, ...] = ()
    is_hidden: bool = False
    sort_order: int = 0
    editable_fields: dict[str, Any] = field(default_factory=dict)
    generated_blocks: tuple[EditorBlockContract, ...] = ()
    manual_blocks: tuple[EditorBlockContract, ...] = ()
    page_actions: dict[str, bool] = field(default_factory=dict)
    style_overrides: dict[str, Any] = field(default_factory=dict)
    page_overrides: dict[str, Any] = field(default_factory=dict)
    validation_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "page"


def stable_page_id(prefix: str, value: Any) -> str:
    return f"{prefix}-{_slug(value)}"


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _row_source_id(row: Mapping[str, Any], index: int) -> str:
    return str(row.get("row_id") or row.get("source_row_id") or row.get("line_number") or index).strip()


def source_row_ids_for_rows(rows: Sequence[Mapping[str, Any]] | None) -> tuple[str, ...]:
    ids: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows or []):
        if not isinstance(row, Mapping):
            continue
        row_id = _row_source_id(row, index)
        if row_id and row_id not in seen:
            ids.append(row_id)
            seen.add(row_id)
    return tuple(ids)


def _normalise_existing_pages(existing_pages: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(existing_pages, (list, tuple)):
        return {}
    pages = {}
    for page in existing_pages:
        if not isinstance(page, Mapping):
            continue
        page_id = str(page.get("page_id") or "").strip()
        if page_id:
            pages[page_id] = dict(page)
    return pages


def _merge_page_overrides(page: EditorPageContract, existing: Mapping[str, Any] | None) -> EditorPageContract:
    if not isinstance(existing, Mapping):
        return page
    manual_blocks = tuple(
        EditorBlockContract(
            block_id=str(block.get("block_id") or "manual-block"),
            block_type=str(block.get("block_type") or "manual"),
            title=str(block.get("title") or ""),
            editable_fields=_as_dict(block.get("editable_fields")),
            style_overrides=_as_dict(block.get("style_overrides")),
            image_binding=_as_dict(block.get("image_binding")),
            source_row_ids=tuple(str(item) for item in block.get("source_row_ids") or []),
            dirty_state=str(block.get("dirty_state") or "clean"),
            validation_status=str(block.get("validation_status") or "unknown"),
        )
        for block in existing.get("manual_blocks") or []
        if isinstance(block, Mapping)
    )
    return EditorPageContract(
        page_id=page.page_id,
        page_type=page.page_type,
        title=str(existing.get("title") or page.title),
        source_day_id=page.source_day_id,
        source_section_id=page.source_section_id,
        source_row_ids=page.source_row_ids,
        is_hidden=bool(existing.get("is_hidden", page.is_hidden)),
        sort_order=int(existing.get("sort_order", page.sort_order) or 0),
        editable_fields=_as_dict(existing.get("editable_fields")) or page.editable_fields,
        generated_blocks=page.generated_blocks,
        manual_blocks=manual_blocks or page.manual_blocks,
        style_overrides=_as_dict(existing.get("style_overrides")) or page.style_overrides,
        page_overrides=_as_dict(existing.get("page_overrides")) or page.page_overrides,
        page_actions=_as_dict(existing.get("page_actions")) or page.page_actions,
        validation_status=str(existing.get("validation_status") or page.validation_status),
    )


def _day_page(day: Mapping[str, Any], rows: Sequence[Mapping[str, Any]] | None, order: int) -> EditorPageContract:
    day_id = str(day.get("day") or day.get("day_id") or day.get("label") or f"Day {order}").strip()
    page_id = stable_page_id("day", day_id)
    source_ids = source_row_ids_for_rows(rows)
    title = str(day.get("title") or day.get("label") or day_id).strip()
    blocks: list[EditorBlockContract] = []
    raw_blocks = day.get("blocks") if isinstance(day.get("blocks"), (list, tuple)) else []
    if raw_blocks:
        for block_index, block in enumerate(raw_blocks):
            if not isinstance(block, Mapping):
                continue
            raw_id = str(block.get("block_id") or f"main-{block_index + 1}").strip()
            block_id = raw_id if raw_id.startswith(f"{page_id}__") else f"{page_id}__{raw_id}"
            blocks.append(
                EditorBlockContract(
                    block_id=block_id,
                    block_type=str(block.get("block_type") or block.get("kind") or "day_content"),
                    title=str(block.get("title") or ""),
                    editable_fields={"content_html": str(block.get("content_html", block.get("html", "")) or "")},
                    source_row_ids=source_ids,
                )
            )
    else:
        blocks.append(
            EditorBlockContract(
                block_id=f"{page_id}__main",
                block_type="day_content",
                editable_fields={"content_html": str(day.get("blocks_html") or "")},
                source_row_ids=source_ids,
            )
        )
    if isinstance(day.get("image"), Mapping):
        blocks.append(
            EditorBlockContract(
                block_id=f"{page_id}__image",
                block_type="image",
                title="Day image",
                image_binding=_as_dict(day.get("image")),
                source_row_ids=source_ids,
            )
        )
    return EditorPageContract(
        page_id=page_id,
        page_type="generated_day",
        title=title,
        source_day_id=day_id,
        source_row_ids=source_ids,
        sort_order=order,
        editable_fields={"title": title, "source_day_id": day_id},
        generated_blocks=tuple(blocks),
        page_actions={"hide": True, "restore": True, "move": False, "duplicate": False, "reset": True},
    )


def _simple_page(page_id: str, page_type: str, title: str, order: int, *, section_id: str = "", editable_fields: Mapping[str, Any] | None = None) -> EditorPageContract:
    return EditorPageContract(
        page_id=page_id,
        page_type=page_type,
        title=title,
        source_section_id=section_id,
        sort_order=order,
        editable_fields=_as_dict(editable_fields),
        generated_blocks=(
            EditorBlockContract(
                block_id=f"{page_id}__main",
                block_type=page_type,
                editable_fields=_as_dict(editable_fields),
            ),
        ),
        page_actions={"hide": True, "restore": True, "move": False, "duplicate": False, "reset": True},
    )


def build_editor_document_pages(
    *,
    payload: Mapping[str, Any],
    grouped_days: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    existing_pages: Any = None,
) -> list[dict[str, Any]]:
    """Build canonical page contracts from the current visual editor payload."""

    existing = _normalise_existing_pages(existing_pages)
    pages: list[EditorPageContract] = [
        _simple_page("cover", "cover", "Cover", 1, editable_fields=_as_dict(payload.get("cover"))),
        _simple_page("summary", "summary", "Trip summary", 2, editable_fields=_as_dict(payload.get("summary"))),
    ]
    grouped_days = grouped_days or {}
    for index, day in enumerate(payload.get("days") or [], start=3):
        if isinstance(day, Mapping):
            day_id = str(day.get("day") or day.get("day_id") or day.get("label") or f"Day {index - 2}")
            pages.append(_day_page(day, grouped_days.get(day_id) or grouped_days.get(str(day.get("label") or "")) or [], index))

    order = len(pages) + 1
    final_pages = payload.get("final_pages") if isinstance(payload.get("final_pages"), Mapping) else {}
    if any(key in final_pages for key in ("whats_included_html", "whats_included_pages_html", "whats_included_text")):
        pages.append(_simple_page("final-whats-included", "final_section", str(final_pages.get("whats_included_title") or "What’s included"), order, section_id="whats_included", editable_fields={
            "whats_included_title": final_pages.get("whats_included_title", "What’s included"),
            "whats_included_html": final_pages.get("whats_included_html", ""),
            "whats_included_pages_html": final_pages.get("whats_included_pages_html", []),
            "whats_included_text": final_pages.get("whats_included_text", ""),
        }))
        order += 1
    if any(key in final_pages for key in ("whats_not_included_html", "whats_not_included_text")):
        pages.append(_simple_page("final-whats-not-included", "final_section", str(final_pages.get("whats_not_included_title") or "What’s not included"), order, section_id="whats_not_included", editable_fields={
            "whats_not_included_title": final_pages.get("whats_not_included_title", "What’s not included"),
            "whats_not_included_html": final_pages.get("whats_not_included_html", ""),
            "whats_not_included_text": final_pages.get("whats_not_included_text", ""),
        }))
        order += 1
    if "important_travel_notes_text" in final_pages:
        pages.append(_simple_page("final-important-travel-notes", "final_section", str(final_pages.get("important_travel_notes_title") or "Important travel notes"), order, section_id="important_travel_notes", editable_fields={
            "important_travel_notes_title": final_pages.get("important_travel_notes_title", "Important travel notes"),
            "important_travel_notes_text": final_pages.get("important_travel_notes_text", ""),
        }))
        order += 1

    merged = [_merge_page_overrides(page, existing.get(page.page_id)).to_dict() for page in pages]
    for page in existing.values():
        if page.get("page_type") == "manual" and page.get("page_id") not in {item["page_id"] for item in merged}:
            copied = dict(page)
            copied.setdefault("sort_order", order)
            copied.setdefault("page_actions", {"hide": True, "restore": True, "move": True, "duplicate": True, "reset": False})
            copied.setdefault("manual_blocks", [])
            merged.append(copied)
            order += 1
    return sorted(merged, key=lambda page: int(page.get("sort_order") or 0))


def hidden_page_ids(document_pages: Any) -> set[str]:
    """Return page IDs explicitly hidden/deleted in the editor page contract."""

    ids: set[str] = set()
    if not isinstance(document_pages, (list, tuple)):
        return ids
    for page in document_pages:
        if not isinstance(page, Mapping):
            continue
        page_id = str(page.get("page_id") or "").strip()
        if page_id and bool(page.get("is_hidden")):
            ids.add(page_id)
    return ids


def final_section_page_id(section_id: str) -> str:
    mapping = {
        "whats_included": "final-whats-included",
        "whats_not_included": "final-whats-not-included",
        "important_travel_notes": "final-important-travel-notes",
    }
    return mapping.get(str(section_id or ""), stable_page_id("final", section_id))


def build_document_pages_from_editor_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build pages from an editor payload when source rows are unavailable."""

    return build_editor_document_pages(payload=payload, grouped_days={}, existing_pages=payload.get("document_pages"))
