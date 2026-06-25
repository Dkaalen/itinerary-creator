"""Compatibility facade for typed editable drafts.

The real editable-draft responsibilities live in model/normalize/lookup/merge
and legacy-bridge modules. This file remains as an import-stability shim.
"""

from __future__ import annotations

from itinerary_generation.editable_draft_model import (
    DRAFT_SCHEMA_VERSION,
    EditableBlock,
    EditableDay,
    EditableDraft,
    EditableFinalPage,
    EditableFinalSection,
)
from itinerary_generation.editable_draft_normalize import (
    _FIELD_TO_SECTION,
    _as_dict,
    _as_text,
    _as_bool,
    _page_html,
    _normalise_pages,
    _normalise_day,
    _normalise_final_sections,
    normalise_editable_draft,
)
from itinerary_generation.editable_draft_lookup import (
    section_by_id,
    day_by_id,
    first_block_html,
)
from itinerary_generation.editable_draft_merge import (
    _merge_mapping,
    _keyed_sequence_by_id,
    merge_editable_drafts,
)
from itinerary_generation.editable_draft_legacy_bridge import mirror_draft_to_legacy_output_edits

__all__ = [
    "DRAFT_SCHEMA_VERSION",
    "EditableBlock",
    "EditableDay",
    "EditableDraft",
    "EditableFinalPage",
    "EditableFinalSection",
    "_FIELD_TO_SECTION",
    "_as_dict",
    "_as_text",
    "_as_bool",
    "_page_html",
    "_normalise_pages",
    "_normalise_day",
    "_normalise_final_sections",
    "normalise_editable_draft",
    "section_by_id",
    "day_by_id",
    "first_block_html",
    "_merge_mapping",
    "_keyed_sequence_by_id",
    "merge_editable_drafts",
    "mirror_draft_to_legacy_output_edits",
]
