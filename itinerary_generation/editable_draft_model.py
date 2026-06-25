"""Typed editable-draft data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

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
    intro_generated_value: str = ""
    intro_generator_version: str = ""
    intro_source_signature: str = ""
    intro_manual_override: bool = False
    blocks_html_generated_value: str = ""
    blocks_html_generator_version: str = ""
    blocks_manual_override: bool = False
    touched_fields: tuple[str, ...] = ()
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

__all__ = [
    "DRAFT_SCHEMA_VERSION",
    "EditableBlock",
    "EditableDay",
    "EditableFinalPage",
    "EditableFinalSection",
    "EditableDraft",
]
