"""Construction and override merging for canonical editor pages."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from itinerary_generation.editor_contract_ids import source_row_ids_for_rows, stable_page_id
from itinerary_generation.editor_contract_model import EditorBlockContract, EditorPageContract


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalise_existing_pages(existing_pages: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(existing_pages, (list, tuple)):
        return {}
    return {
        str(page.get("page_id") or "").strip(): dict(page)
        for page in existing_pages if isinstance(page, Mapping) and str(page.get("page_id") or "").strip()
    }


def _manual_blocks(existing: Mapping[str, Any]) -> tuple[EditorBlockContract, ...]:
    return tuple(
        EditorBlockContract(
            block_id=str(block.get("block_id") or "manual-block"), block_type=str(block.get("block_type") or "manual"),
            title=str(block.get("title") or ""), editable_fields=_as_dict(block.get("editable_fields")),
            style_overrides=_as_dict(block.get("style_overrides")), image_binding=_as_dict(block.get("image_binding")),
            source_row_ids=tuple(str(item) for item in block.get("source_row_ids") or []),
            dirty_state=str(block.get("dirty_state") or "clean"), validation_status=str(block.get("validation_status") or "unknown"),
        )
        for block in existing.get("manual_blocks") or [] if isinstance(block, Mapping)
    )


def _merge_page_overrides(page: EditorPageContract, existing: Mapping[str, Any] | None) -> EditorPageContract:
    if not isinstance(existing, Mapping):
        return page
    page_actions = _as_dict(existing.get("page_actions")) or page.page_actions
    if page.page_type == "generated_day":
        page_actions = {**page_actions, "move": False, "duplicate": False}
    return EditorPageContract(
        page_id=page.page_id, page_type=page.page_type, title=str(existing.get("title") or page.title),
        source_day_id=page.source_day_id, source_section_id=page.source_section_id, source_row_ids=page.source_row_ids,
        is_hidden=bool(existing.get("is_hidden", page.is_hidden)),
        sort_order=page.sort_order if page.page_type == "generated_day" else int(existing.get("sort_order", page.sort_order) or 0),
        editable_fields=_as_dict(existing.get("editable_fields")) or page.editable_fields, generated_blocks=page.generated_blocks,
        manual_blocks=_manual_blocks(existing) or page.manual_blocks,
        style_overrides=_as_dict(existing.get("style_overrides")) or page.style_overrides,
        page_overrides=_as_dict(existing.get("page_overrides")) or page.page_overrides,
        page_actions=page_actions,
        validation_status=str(existing.get("validation_status") or page.validation_status),
    )


def _day_blocks(page_id: str, day: Mapping[str, Any], source_ids: tuple[str, ...]) -> tuple[EditorBlockContract, ...]:
    blocks: list[EditorBlockContract] = []
    raw_blocks = day.get("blocks") if isinstance(day.get("blocks"), (list, tuple)) else []
    for index, block in enumerate(raw_blocks):
        if not isinstance(block, Mapping):
            continue
        raw_id = str(block.get("block_id") or f"main-{index + 1}").strip()
        blocks.append(EditorBlockContract(
            block_id=raw_id if raw_id.startswith(f"{page_id}__") else f"{page_id}__{raw_id}",
            block_type=str(block.get("block_type") or block.get("kind") or "day_content"), title=str(block.get("title") or ""),
            editable_fields={"content_html": str(block.get("content_html", block.get("html", "")) or "")}, source_row_ids=source_ids,
        ))
    if not blocks:
        blocks.append(EditorBlockContract(block_id=f"{page_id}__main", block_type="day_content", editable_fields={"content_html": str(day.get("blocks_html") or "")}, source_row_ids=source_ids))
    if isinstance(day.get("image"), Mapping):
        blocks.append(EditorBlockContract(block_id=f"{page_id}__image", block_type="image", title="Day image", image_binding=_as_dict(day.get("image")), source_row_ids=source_ids))
    return tuple(blocks)


def _day_page(day: Mapping[str, Any], rows: Sequence[Mapping[str, Any]] | None, order: int) -> EditorPageContract:
    day_id = str(day.get("day") or day.get("day_id") or day.get("label") or f"Day {order}").strip()
    page_id, source_ids = stable_page_id("day", day_id), source_row_ids_for_rows(rows)
    title = str(day.get("title") or day.get("label") or day_id).strip()
    return EditorPageContract(
        page_id=page_id, page_type="generated_day", title=title, source_day_id=day_id, source_row_ids=source_ids,
        sort_order=order, editable_fields={"title": title, "source_day_id": day_id}, generated_blocks=_day_blocks(page_id, day, source_ids),
        page_actions={"hide": True, "restore": True, "move": False, "duplicate": False, "reset": True},
    )


def _simple_page(page_id: str, page_type: str, title: str, order: int, *, section_id: str = "", editable_fields: Mapping[str, Any] | None = None) -> EditorPageContract:
    fields = _as_dict(editable_fields)
    return EditorPageContract(
        page_id=page_id, page_type=page_type, title=title, source_section_id=section_id, sort_order=order,
        editable_fields=fields, generated_blocks=(EditorBlockContract(block_id=f"{page_id}__main", block_type=page_type, editable_fields=fields),),
        page_actions={"hide": True, "restore": True, "move": True, "duplicate": False, "reset": True},
    )


def _generated_pages(payload: Mapping[str, Any], grouped_days: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[EditorPageContract]:
    pages = [_simple_page("cover", "cover", "Cover", 1, editable_fields=_as_dict(payload.get("cover"))), _simple_page("summary", "summary", "Trip summary", 2, editable_fields=_as_dict(payload.get("summary")))]
    for index, day in enumerate(payload.get("days") or [], start=3):
        if isinstance(day, Mapping):
            day_id = str(day.get("day") or day.get("day_id") or day.get("label") or f"Day {index - 2}")
            pages.append(_day_page(day, grouped_days.get(day_id) or grouped_days.get(str(day.get("label") or "")) or [], index))
    return pages


def _append_final_pages(pages: list[EditorPageContract], final_pages: Mapping[str, Any]) -> None:
    order = len(pages) + 1
    specs = (
        ("final-whats-included", "whats_included", "What’s included", ("whats_included_html", "whats_included_pages_html", "whats_included_text")),
        ("final-whats-not-included", "whats_not_included", "What’s not included", ("whats_not_included_html", "whats_not_included_text")),
        ("final-important-travel-notes", "important_travel_notes", "Important travel notes", ("important_travel_notes_text",)),
    )
    for page_id, section_id, default_title, keys in specs:
        if not any(key in final_pages for key in keys):
            continue
        title_key = f"{section_id}_title"
        fields = {title_key: final_pages.get(title_key, default_title), **{key: final_pages.get(key, [] if key.endswith("pages_html") else "") for key in keys}}
        pages.append(_simple_page(page_id, "final_section", str(final_pages.get(title_key) or default_title), order, section_id=section_id, editable_fields=fields))
        order += 1


def build_editor_document_pages(*, payload: Mapping[str, Any], grouped_days: Mapping[str, Sequence[Mapping[str, Any]]] | None = None, existing_pages: Any = None) -> list[dict[str, Any]]:
    existing = _normalise_existing_pages(existing_pages)
    pages = _generated_pages(payload, grouped_days or {})
    final_pages = payload.get("final_pages") if isinstance(payload.get("final_pages"), Mapping) else {}
    _append_final_pages(pages, final_pages)
    merged = [_merge_page_overrides(page, existing.get(page.page_id)).to_dict() for page in pages]
    known = {item["page_id"] for item in merged}
    order = len(merged) + 1
    for page in existing.values():
        if page.get("page_type") == "manual" and page.get("page_id") not in known:
            copied = dict(page); copied.setdefault("sort_order", order)
            copied.setdefault("page_actions", {"hide": True, "restore": True, "move": True, "duplicate": True, "reset": False})
            copied.setdefault("manual_blocks", []); merged.append(copied); order += 1
    return sorted(merged, key=lambda page: int(page.get("sort_order") or 0))


def build_document_pages_from_editor_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return build_editor_document_pages(payload=payload, grouped_days={}, existing_pages=payload.get("document_pages"))
