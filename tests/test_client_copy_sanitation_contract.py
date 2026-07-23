from itinerary_generation.client_sanitizer import sanitize_render_document_client_output
from itinerary_generation.render_model import RenderBlock, RenderDay, RenderDocument, RenderMetaLine


def test_field_aware_sanitizer_removes_invalid_customer_fields_without_touching_identity():
    document = RenderDocument(
        title="Route: Route: the The The Little Mermaid",
        warnings=["technical warning TBD"],
        labels={"page_id": "TBD-internal"},
        days=[
            RenderDay(
                day="Day 1",
                number="1",
                city="Copenhagen",
                title="Route: Route: Copenhagen",
                intro="Supplier note: do not show this",
                source_row_ids=["row-1"],
                labels={"intro_decision_source": "activity_day_intro"},
                blocks=[
                    RenderBlock(
                        kind="activity",
                        row_id="row-1",
                        title="the The The Little Mermaid",
                        meta=[
                            RenderMetaLine("Time", "TBD"),
                            RenderMetaLine("Meeting point", "TBC"),
                            RenderMetaLine("Duration", "2 hours"),
                        ],
                        description="Route: Route: Waterfront walk",
                        content_html='<p data-id="TBD">the The The Little Mermaid</p>',
                        source_row_ids=["row-1"],
                    )
                ],
            )
        ],
    )

    sanitize_render_document_client_output(document)

    assert document.title == "Route: the Little Mermaid"
    assert document.warnings == ["technical warning TBD"]
    assert document.labels == {"page_id": "TBD-internal"}
    day = document.days[0]
    assert day.source_row_ids == ["row-1"]
    assert day.labels["intro_decision_source"] == "activity_day_intro"
    assert day.intro == ""
    block = day.blocks[0]
    assert [(item.label, item.value) for item in block.meta] == [("Duration", "2 hours")]
    assert block.title == "the Little Mermaid"
    assert block.description == "Route: Waterfront walk"
    assert block.content_html == '<p data-id="TBD">the Little Mermaid</p>'
