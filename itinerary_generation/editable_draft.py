"""Typed visual-editor draft model.

The visual editor still renders rich day/final-page content as HTML in the
browser, but the saved editor contract should not be a loose collection of
legacy top-level HTML keys.  This module provides a typed draft envelope and a
compatibility mirror so the existing preview/PDF renderer can keep working
while new saves prefer structured JSON under ``output_edits['editor_draft']``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


DRAFT_SCHEMA_VERSION = 3


@dataclass(frozen=True)
class EditableBlock:
    """A single editable content block on a day page."""

    block_id: str
    kind: str = "day_content"
    title: str = ""
    content_html: str = ""


@dataclass(frozen=True)
class EditableDay:
    """Typed editor state for one visible itinerary day."""

    day_id: str
    label: str = ""
    date: str = ""
    title: str = ""
    city: str = ""
    intro: str = ""
    blocks: tuple[EditableBlock, ...] = ()
    image: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EditableFinalPage:
    """One editable page inside a final itinerary section."""

    page_id: str
    content_html: str = ""


@dataclass(frozen=True)
class EditableFinalSection:
    """Typed editor state for included/excluded/notes final sections."""

    section_id: str
    title: str
    pages: tuple[EditableFinalPage, ...] = ()
    text: str = ""
    content_html: str = ""


@dataclass(frozen=True)
class EditableDraft:
    """Stable editor draft contract saved in output_edits."""

    schema_version: int = DRAFT_SCHEMA_VERSION
    cover: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    days: tuple[EditableDay, ...] = ()
    final_sections: tuple[EditableFinalSection, ...] = ()
    workflow: dict[str, Any] = field(default_factory=dict)
    issue_flags: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _page_html(value: Any) -> str:
    if isinstance(value, Mapping):
        return _as_text(value.get("html", ""))
    return _as_text(value)


def _normalise_pages(value: Any) -> tuple[EditableFinalPage, ...]:
    values = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
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

    raw_blocks = value.get("blocks")
    blocks: list[EditableBlock] = []
    if isinstance(raw_blocks, list):
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
        blocks=tuple(blocks),
        image=_as_dict(value.get("image")),
    )


def _normalise_final_sections(data: Mapping[str, Any]) -> tuple[EditableFinalSection, ...]:
    final_pages = _as_dict(data.get("final_pages"))
    sections: dict[str, EditableFinalSection] = {}

    if "whats_included_pages_html" in final_pages:
        section_id, title = _FIELD_TO_SECTION["whats_included_pages_html"]
        sections[section_id] = EditableFinalSection(
            section_id=section_id,
            title=title,
            pages=_normalise_pages(final_pages.get("whats_included_pages_html")),
            text=_as_text(final_pages.get("whats_included_text", "")),
            content_html=_as_text(final_pages.get("whats_included_html", "")),
        )
    elif "whats_included_html" in final_pages or "whats_included_text" in final_pages:
        section_id, title = _FIELD_TO_SECTION["whats_included_html"]
        content_html = _as_text(final_pages.get("whats_included_html", ""))
        sections[section_id] = EditableFinalSection(
            section_id=section_id,
            title=title,
            pages=(EditableFinalPage("page-1", content_html),) if content_html else (),
            text=_as_text(final_pages.get("whats_included_text", "")),
            content_html=content_html,
        )

    if "whats_not_included_html" in final_pages or "whats_not_included_text" in final_pages:
        section_id, title = _FIELD_TO_SECTION["whats_not_included_html"]
        content_html = _as_text(final_pages.get("whats_not_included_html", ""))
        sections[section_id] = EditableFinalSection(
            section_id=section_id,
            title=title,
            pages=(EditableFinalPage("page-1", content_html),) if content_html else (),
            text=_as_text(final_pages.get("whats_not_included_text", "")),
            content_html=content_html,
        )

    if "important_travel_notes_text" in final_pages:
        section_id, title = _FIELD_TO_SECTION["important_travel_notes_text"]
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
        workflow=_as_dict(source.get("workflow")),
        issue_flags=issue_flags,
    )
    return draft.to_dict()


def section_by_id(editor_draft: Mapping[str, Any], section_id: str) -> dict[str, Any]:
    for section in editor_draft.get("final_sections") or []:
        if isinstance(section, Mapping) and section.get("section_id") == section_id:
            return dict(section)
    return {}


def day_by_id(editor_draft: Mapping[str, Any], day_id: str) -> dict[str, Any]:
    for day in editor_draft.get("days") or []:
        if isinstance(day, Mapping) and str(day.get("day_id") or day.get("day") or "") == str(day_id):
            return dict(day)
    return {}


def first_block_html(day: Mapping[str, Any]) -> str | None:
    blocks = day.get("blocks") if isinstance(day, Mapping) else None
    if not isinstance(blocks, (list, tuple)) or not blocks:
        return None
    block = blocks[0]
    if not isinstance(block, Mapping):
        return None
    return _as_text(block.get("content_html", block.get("html", "")))


def mirror_draft_to_legacy_output_edits(output_edits: dict[str, Any], editor_draft: Mapping[str, Any]) -> None:
    """Mirror typed draft values to legacy keys used by existing renderers.

    The typed ``editor_draft`` remains the preferred save contract.  The mirror
    lets preview/PDF/editor recovery continue to work until those layers are
    rewritten to consume typed draft fields directly.
    """

    if not isinstance(output_edits, dict) or not isinstance(editor_draft, Mapping):
        return

    output_edits["editor_draft"] = dict(editor_draft)

    for key, value in _as_dict(editor_draft.get("cover")).items():
        if key == "destinations_line":
            output_edits[key] = _as_text(value)
        else:
            output_edits[key] = _as_text(value).strip()

    summary = _as_dict(editor_draft.get("summary"))
    if isinstance(summary.get("trip_glance"), Mapping):
        output_edits["trip_glance"] = {str(key).strip(): _as_text(value).strip() for key, value in summary["trip_glance"].items() if str(key).strip()}
    if isinstance(summary.get("journey_arc"), list):
        output_edits["journey_arc"] = [dict(row) for row in summary["journey_arc"] if isinstance(row, Mapping)]

    days = output_edits.setdefault("days", {})
    for draft_day in editor_draft.get("days") or []:
        if not isinstance(draft_day, Mapping):
            continue
        day_id = _as_text(draft_day.get("day_id") or draft_day.get("day") or draft_day.get("label", "")).strip()
        if not day_id:
            continue
        day_edits = days.setdefault(day_id, {})
        for field in ("title", "city", "intro"):
            if field in draft_day:
                day_edits[field] = _as_text(draft_day.get(field, "")).strip()
        block_html = first_block_html(draft_day)
        if block_html is not None:
            day_edits["blocks_html"] = block_html

    included = section_by_id(editor_draft, "whats_included")
    if included:
        pages = included.get("pages") or []
        page_htmls = [_page_html(page) for page in pages if isinstance(page, Mapping) or page is not None]
        if page_htmls:
            output_edits["whats_included_pages_html"] = page_htmls
            output_edits["whats_included_html"] = ""
            output_edits["whats_included_text"] = _as_text(included.get("text", ""))
        elif "content_html" in included:
            output_edits["whats_included_html"] = _as_text(included.get("content_html", ""))
            output_edits.pop("whats_included_pages_html", None)
            output_edits["whats_included_text"] = _as_text(included.get("text", ""))

    excluded = section_by_id(editor_draft, "whats_not_included")
    if excluded:
        html = _as_text(excluded.get("content_html", ""))
        if not html and excluded.get("pages"):
            html = _page_html(excluded["pages"][0])
        if html:
            output_edits["whats_not_included_html"] = html
            output_edits["whats_not_included_text"] = ""
        elif "text" in excluded:
            output_edits["whats_not_included_text"] = _as_text(excluded.get("text", "")).strip()

    notes = section_by_id(editor_draft, "important_travel_notes")
    if notes:
        output_edits["important_travel_notes_text"] = _as_text(notes.get("text", "")).strip()

    workflow = _as_dict(editor_draft.get("workflow"))
    if "pictures_added" in workflow:
        output_edits["pictures_added"] = bool(workflow.get("pictures_added"))

    issue_flags = [dict(flag) for flag in editor_draft.get("issue_flags") or [] if isinstance(flag, Mapping)]
    if issue_flags:
        output_edits["visual_editor_issue_flags"] = issue_flags
