"""Editable-draft merge helpers."""

from __future__ import annotations

from typing import Any, Mapping

from itinerary_generation.editable_draft_model import DRAFT_SCHEMA_VERSION
from itinerary_generation.editable_draft_normalize import _as_dict, _as_text, normalise_editable_draft

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
        touched = set(incoming_day.get("touched_fields") or [])
        # Full drafts from older callers may not include touched_fields. Treat a
        # missing list as a complete day, but use the key-aware list for compact
        # autosave deltas so image-only saves do not blank text/body fields.
        full_day = not touched
        fields = (
            "label",
            "date",
            "title",
            "city",
            "intro",
            "intro_generated_value",
            "intro_generator_version",
            "intro_source_signature",
            "intro_manual_override",
            "blocks_html_generated_value",
            "blocks_html_generator_version",
            "blocks_manual_override",
            "image",
        )
        if day_id in day_indexes:
            copied = dict(days[day_indexes[day_id]])
            for field in fields:
                if full_day or field in touched:
                    copied[field] = incoming_day.get(field, copied.get(field, {} if field == "image" else ""))
            if full_day or "blocks" in touched or "blocks_html" in touched:
                copied["blocks"] = list(incoming_day.get("blocks") or [])
            copied["touched_fields"] = tuple(sorted(set(copied.get("touched_fields") or ()) | touched))
            days[day_indexes[day_id]] = copied
        else:
            copied = dict(incoming_day)
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

__all__ = ["_merge_mapping", "_keyed_sequence_by_id", "merge_editable_drafts"]
