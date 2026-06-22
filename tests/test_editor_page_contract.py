from itinerary_generation.editor_page_contract import build_editor_document_pages
from itinerary_generation.editable_draft import normalise_editable_draft
from visual_editor_component.editor_payload_builder import build_visual_editor_payload


def test_editor_page_contract_builds_stable_generated_pages_and_blocks():
    rows = [
        {"row_id": "r1", "day": "Day 1", "type": "Activity", "effective_type": "Activity", "city": "Bergen", "title": "Fjord cruise"},
    ]
    payload = {
        "days": [{"day": "Day 1", "title": "Bergen", "blocks_html": "<div>Activity</div>"}],
        "final_pages": {"whats_included_html": "<div>Included</div>", "important_travel_notes_text": "Bring ID"},
    }

    pages = build_editor_document_pages(payload=payload, grouped_days={"Day 1": rows})

    page_ids = [page["page_id"] for page in pages]
    assert page_ids[:3] == ["cover", "summary", "day-day-1"]
    day_page = pages[2]
    assert day_page["page_type"] == "generated_day"
    assert day_page["source_row_ids"] == ("r1",)
    assert day_page["generated_blocks"][0]["block_id"] == "day-day-1__main"


def test_editor_page_contract_preserves_generated_page_hide_override():
    payload = {
        "days": [{"day": "Day 1", "title": "Oslo", "blocks_html": ""}],
        "final_pages": {},
    }
    existing_pages = [{"page_id": "day-day-1", "page_type": "generated_day", "title": "Old", "is_hidden": True}]

    pages = build_editor_document_pages(payload=payload, grouped_days={"Day 1": []}, existing_pages=existing_pages)

    day_page = next(page for page in pages if page["page_id"] == "day-day-1")
    assert day_page["is_hidden"] is True
    assert day_page["title"] == "Old"


def test_typed_draft_includes_document_pages():
    draft = normalise_editable_draft({
        "days": [{"day": "Day 1", "blocks_html": "<div>Text</div>"}],
        "final_pages": {"whats_not_included_html": "<div>Excluded</div>"},
    })

    assert draft["document_pages"][0]["page_id"] == "cover"
    assert any(page["page_id"] == "day-day-1" for page in draft["document_pages"])


def test_visual_editor_payload_exposes_document_pages_contract():
    rows = [{"row_id": "r1", "day": "Day 1", "type": "Activity", "effective_type": "Activity", "city": "Oslo", "title": "Walk"}]

    payload = build_visual_editor_payload(rows, {"Day 1": rows}, {"days": {}, "pictures_added": False})

    assert payload["document_pages"][0]["page_id"] == "cover"
    assert payload["editor_draft"]["document_pages"]
    day_page = next(page for page in payload["document_pages"] if page["page_type"] == "generated_day")
    assert day_page["source_row_ids"] == ("r1",)
