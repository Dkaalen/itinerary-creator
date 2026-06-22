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

from itinerary_generation.editor_page_contract import build_document_pages_from_editor_payload


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
    document_pages: tuple[dict[str, Any], ...] = ()
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
        document_pages=tuple(page for page in build_document_pages_from_editor_payload(source) if isinstance(page, Mapping)),
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



def _merge_mapping(existing: Any, incoming: Any) -> dict[str, Any]:
    """Return a shallow mapping merge that treats incoming blank values as real edits."""

    base = _as_dict(existing)
    for key, value in _as_dict(incoming).items():
        base[str(key)] = value
    return base


def _keyed_sequence_by_id(values: Any, *candidate_keys: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Normalize a draft sequence and return stable id -> index lookup."""

    sequence: list[dict[str, Any]] = []
    index_by_id: dict[str, int] = {}
    if not isinstance(values, (list, tuple)):
        return sequence, index_by_id
    for item in values:
        if not isinstance(item, Mapping):
            continue
        copied = dict(item)
        item_id = ""
        for key in candidate_keys:
            item_id = _as_text(copied.get(key, "")).strip()
            if item_id:
                break
        if not item_id:
            continue
        index_by_id[item_id] = len(sequence)
        sequence.append(copied)
    return sequence, index_by_id


def merge_editable_drafts(existing: Mapping[str, Any] | None, incoming: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge a partial editor save into the stored typed draft.

    The browser intentionally sends small payloads for normal "save for now"
    actions.  Replacing ``output_edits['editor_draft']`` with that partial draft
    would lose untouched days, copied blocks, final pages, and workflow state.
    This merge keeps ``EditableDraft`` as the source of truth by applying edits
    by stable day/section identity while preserving untouched typed state.
    """

    existing_draft = normalise_editable_draft(existing or {})
    incoming_draft = normalise_editable_draft(incoming or {})

    merged: dict[str, Any] = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "cover": _merge_mapping(existing_draft.get("cover"), incoming_draft.get("cover")),
        "summary": _merge_mapping(existing_draft.get("summary"), incoming_draft.get("summary")),
        "days": [],
        "final_sections": [],
        "document_pages": [],
        "workflow": _merge_mapping(existing_draft.get("workflow"), incoming_draft.get("workflow")),
        "issue_flags": [],
    }

    days, day_indexes = _keyed_sequence_by_id(existing_draft.get("days"), "day_id", "day", "label")
    for incoming_day in incoming_draft.get("days") or []:
        if not isinstance(incoming_day, Mapping):
            continue
        day_id = _as_text(incoming_day.get("day_id") or incoming_day.get("day") or incoming_day.get("label", "")).strip()
        if not day_id:
            continue
        copied = dict(incoming_day)
        if day_id in day_indexes:
            days[day_indexes[day_id]] = copied
        else:
            day_indexes[day_id] = len(days)
            days.append(copied)
    merged["days"] = days

    sections, section_indexes = _keyed_sequence_by_id(existing_draft.get("final_sections"), "section_id")
    for incoming_section in incoming_draft.get("final_sections") or []:
        if not isinstance(incoming_section, Mapping):
            continue
        section_id = _as_text(incoming_section.get("section_id", "")).strip()
        if not section_id:
            continue
        copied = dict(incoming_section)
        if section_id in section_indexes:
            sections[section_indexes[section_id]] = copied
        else:
            section_indexes[section_id] = len(sections)
            sections.append(copied)
    merged["final_sections"] = sections

    incoming_pages = incoming_draft.get("document_pages") if isinstance(incoming_draft.get("document_pages"), (list, tuple)) else []
    existing_pages = existing_draft.get("document_pages") if isinstance(existing_draft.get("document_pages"), (list, tuple)) else []
    merged["document_pages"] = list(incoming_pages or existing_pages or [])

    seen_flags: set[tuple[str, str, str]] = set()
    flags: list[dict[str, Any]] = []
    for source in (existing_draft.get("issue_flags"), incoming_draft.get("issue_flags")):
        for flag in source or []:
            if not isinstance(flag, Mapping):
                continue
            copied = dict(flag)
            key = (_as_text(copied.get("key", "")), _as_text(copied.get("original", "")), _as_text(copied.get("corrected", "")))
            if key in seen_flags:
                continue
            seen_flags.add(key)
            flags.append(copied)
    merged["issue_flags"] = flags

    return normalise_editable_draft(merged)


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
        # The Streamlit workflow state is the source of truth once picture review
        # has been activated. Older/stale editor payloads can still carry
        # workflow.pictures_added=false; those must not turn off pictures after
        # the user has clicked Add pictures. A positive editor value may still
        # promote the state for restored projects.
        editor_pictures_added = bool(workflow.get("pictures_added"))
        output_edits["pictures_added"] = bool(output_edits.get("pictures_added")) or editor_pictures_added

    issue_flags = [dict(flag) for flag in editor_draft.get("issue_flags") or [] if isinstance(flag, Mapping)]
    if issue_flags:
        output_edits["visual_editor_issue_flags"] = issue_flags
