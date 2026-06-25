"""Value models for the canonical visual-editor page contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

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
