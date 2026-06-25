"""Public compatibility facade for the canonical editor page contract."""

from itinerary_generation.editor_contract_builder import build_document_pages_from_editor_payload, build_editor_document_pages
from itinerary_generation.editor_contract_ids import final_section_page_id, source_row_ids_for_rows, stable_page_id
from itinerary_generation.editor_contract_model import EditorBlockContract, EditorPageContract, PAGE_CONTRACT_SCHEMA_VERSION
from itinerary_generation.editor_contract_queries import (
    document_pages_from_draft, final_section_is_hidden, hidden_page_ids, manual_pages_from_document_pages,
    manual_pages_from_draft, ordered_page_ids, page_is_hidden, page_order_from_document_pages, page_order_from_draft,
)

__all__ = [
    "PAGE_CONTRACT_SCHEMA_VERSION", "EditorBlockContract", "EditorPageContract",
    "build_document_pages_from_editor_payload", "build_editor_document_pages", "document_pages_from_draft",
    "final_section_is_hidden", "final_section_page_id", "hidden_page_ids", "manual_pages_from_document_pages",
    "manual_pages_from_draft", "ordered_page_ids", "page_is_hidden", "page_order_from_document_pages",
    "page_order_from_draft", "source_row_ids_for_rows", "stable_page_id",
]
