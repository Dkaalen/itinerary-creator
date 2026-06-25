"""Editable-draft normalization helpers."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.editor_page_contract import build_document_pages_from_editor_payload
from itinerary_generation.editable_draft_model import (
    DRAFT_SCHEMA_VERSION,
    EditableBlock,
    EditableDay,
    EditableDraft,
    EditableFinalPage,
    EditableFinalSection,
)

_FIELD_TO_SECTION = {
    "whats_included_pages_html": ("whats_included", "What's included"),
    "whats_included_html": ("whats_included", "What's included"),
    "whats_not_included_html": ("whats_not_included", "What's not included"),
    "important_travel_notes_text": ("important_travel_notes", "Important travel notes"),
}


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_text(value: Any) -> str:
    return str(value) if value is not None else ""


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _page_html(value: Any) -> str:
    if isinstance(value, Mapping):
        return _as_text(value.get("content_html", value.get("html", "")))
    return _as_text(value)


def _normalise_pages(value: Any) -> tuple[EditableFinalPage, ...]:
    values = value if isinstance(value, (list, tuple)) else ([value] if value not in (None, "") else [])
    pages: list[EditableFinalPage] = []
    for index, page in enumerate(values):
        pages.append(EditableFinalPage(page_id=f"page-{index + 1}", content_html=_page_html(page)))
    return tuple(pages)


def _normalise_day(value: Any, index: int) -> EditableDay | None:
    if not isinstance(value, Mapping):
        return None
    day_id = _as_text(value.get("day") or value.get("day_id") or value.get("label") or f"Day {index + 1}").strip()
    if not day_id:
        return None

    raw_touched = value.get("touched_fields")
    if isinstance(raw_touched, (list, tuple)):
        touched_fields = tuple(str(item) for item in raw_touched if str(item))
    else:
        touched_fields = tuple(
            field
            for field in (
                "label",
                "date",
                "title",
                "city",
                "intro",
                "intro_generated_value",
                "intro_generator_version",
                "intro_source_signature",
                "intro_manual_override",
                "blocks",
                "blocks_html",
                "blocks_html_generated_value",
                "blocks_html_generator_version",
                "blocks_manual_override",
                "image",
            )
            if field in value
        )

    raw_blocks = value.get("blocks")
    blocks: list[EditableBlock] = []
    if isinstance(raw_blocks, (list, tuple)):
        for block_index, block in enumerate(raw_blocks):
            if not isinstance(block, Mapping):
                continue
            blocks.append(
                EditableBlock(
                    block_id=_as_text(block.get("block_id") or f"main-{block_index + 1}"),
                    kind=_as_text(block.get("kind") or "day_content"),
                    title=_as_text(block.get("title", "")),
                    content_html=_as_text(block.get("content_html", block.get("html", ""))),
                )
            )
    elif "blocks_html" in value:
        # Compatibility import from the old editor payload.  Store it inside a
        # typed block so new saves have a predictable shape.
        blocks.append(EditableBlock(block_id="main", kind="day_content", content_html=_as_text(value.get("blocks_html", ""))))

    return EditableDay(
        day_id=day_id,
        label=_as_text(value.get("label") or day_id),
        date=_as_text(value.get("date", "")),
        title=_as_text(value.get("title", "")),
        city=_as_text(value.get("city", "")),
        intro=_as_text(value.get("intro", "")),
        intro_generated_value=_as_text(value.get("intro_generated_value", "")),
        intro_generator_version=_as_text(value.get("intro_generator_version", "")),
        intro_source_signature=_as_text(value.get("intro_source_signature", "")),
        intro_manual_override=_as_bool(value.get("intro_manual_override", ("intro" in value and "intro_generated_value" not in value))),
        blocks_html_generated_value=_as_text(value.get("blocks_html_generated_value", "")),
        blocks_html_generator_version=_as_text(value.get("blocks_html_generator_version", "")),
        blocks_manual_override=_as_bool(value.get("blocks_manual_override", (("blocks_html" in value or "blocks" in value) and "blocks_html_generated_value" not in value))),
        touched_fields=touched_fields,
        blocks=tuple(blocks),
        image=_as_dict(value.get("image")),
    )


def _normalise_final_sections(data: Mapping[str, Any]) -> tuple[EditableFinalSection, ...]:
    final_pages = _as_dict(data.get("final_pages"))
    sections: dict[str, EditableFinalSection] = {}

    if "whats_included_pages_html" in final_pages:
        section_id, default_title = _FIELD_TO_SECTION["whats_included_pages_html"]
        title = _as_text(final_pages.get("whats_included_title") or default_title)
        sections[section_id] = EditableFinalSection(
            section_id=section_id,
            title=title,
            pages=_normalise_pages(final_pages.get("whats_included_pages_html")),
            text=_as_text(final_pages.get("whats_included_text", "")),
            content_html=_as_text(final_pages.get("whats_included_html", "")),
        )
    elif "whats_included_html" in final_pages or "whats_included_text" in final_pages:
        section_id, default_title = _FIELD_TO_SECTION["whats_included_html"]
        title = _as_text(final_pages.get("whats_included_title") or default_title)
        content_html = _as_text(final_pages.get("whats_included_html", ""))
        sections[section_id] = EditableFinalSection(
            section_id=section_id,
            title=title,
            pages=(EditableFinalPage("page-1", content_html),) if content_html else (),
            text=_as_text(final_pages.get("whats_included_text", "")),
            content_html=content_html,
        )

    if "whats_not_included_html" in final_pages or "whats_not_included_text" in final_pages:
        section_id, default_title = _FIELD_TO_SECTION["whats_not_included_html"]
        title = _as_text(final_pages.get("whats_not_included_title") or default_title)
        content_html = _as_text(final_pages.get("whats_not_included_html", ""))
        sections[section_id] = EditableFinalSection(
            section_id=section_id,
            title=title,
            pages=(EditableFinalPage("page-1", content_html),) if content_html else (),
            text=_as_text(final_pages.get("whats_not_included_text", "")),
            content_html=content_html,
        )

    if "important_travel_notes_text" in final_pages:
        section_id, default_title = _FIELD_TO_SECTION["important_travel_notes_text"]
        title = _as_text(final_pages.get("important_travel_notes_title") or default_title)
        sections[section_id] = EditableFinalSection(
            section_id=section_id,
            title=title,
            text=_as_text(final_pages.get("important_travel_notes_text", "")),
        )

    # Allow a client to send final_sections directly and let those values
    # override legacy-derived sections.
    for raw_section in data.get("final_sections") or []:
        if not isinstance(raw_section, Mapping):
            continue
        section_id = _as_text(raw_section.get("section_id", "")).strip()
        if not section_id:
            continue
        sections[section_id] = EditableFinalSection(
            section_id=section_id,
            title=_as_text(raw_section.get("title") or section_id.replace("_", " ").title()),
            pages=_normalise_pages(raw_section.get("pages", [])),
            text=_as_text(raw_section.get("text", "")),
            content_html=_as_text(raw_section.get("content_html", "")),
        )

    return tuple(sections.values())


def normalise_editable_draft(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a typed editor draft dict from a full or partial editor payload."""

    if not isinstance(data, Mapping):
        return EditableDraft().to_dict()

    raw_draft = _as_dict(data.get("editor_draft"))
    source = {**data, **raw_draft} if raw_draft else data
    days = tuple(
        day for index, value in enumerate(source.get("days") or [])
        if (day := _normalise_day(value, index)) is not None
    )
    issue_flags = tuple(flag for flag in (source.get("issue_flags") or []) if isinstance(flag, Mapping))
    draft = EditableDraft(
        schema_version=DRAFT_SCHEMA_VERSION,
        cover=_as_dict(source.get("cover")),
        summary=_as_dict(source.get("summary")),
        days=days,
        final_sections=_normalise_final_sections(source),
        document_pages=tuple(page for page in build_document_pages_from_editor_payload(source) if isinstance(page, Mapping)),
        workflow=_as_dict(source.get("workflow")),
        issue_flags=issue_flags,
    )
    return draft.to_dict()

__all__ = [
    "_FIELD_TO_SECTION",
    "_as_dict",
    "_as_text",
    "_as_bool",
    "_page_html",
    "_normalise_pages",
    "_normalise_day",
    "_normalise_final_sections",
    "normalise_editable_draft",
]
