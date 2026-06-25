"""Compatibility facade for typed editable drafts."""

from __future__ import annotations

from itinerary_generation.editable_draft_core import (
    EditableBlock,
    EditableDay,
    EditableDraft,
    EditableFinalPage,
    EditableFinalSection,
    normalise_editable_draft,
    section_by_id,
    day_by_id,
    first_block_html,
    merge_editable_drafts,
    mirror_draft_to_legacy_output_edits,
)

__all__ = ['EditableBlock', 'EditableDay', 'EditableDraft', 'EditableFinalPage', 'EditableFinalSection', 'normalise_editable_draft', 'section_by_id', 'day_by_id', 'first_block_html', 'merge_editable_drafts', 'mirror_draft_to_legacy_output_edits']
