"""Debug/internal-review appendix rendering for typed PDF export."""

from __future__ import annotations

from itinerary_generation.render_model import RenderDocument
from pdf_exporter_modules.render_flowables import add_premium_rule
from pdf_exporter_modules.story import add_paragraph


def render_internal_review_appendix(render_document: RenderDocument, story, styles):
    add_paragraph(story, "Internal Review Notes", styles["page_title"])
    add_premium_rule(story)
    day_count = len(render_document.days or [])
    final_count = len(render_document.final_sections or [])
    add_paragraph(story, f"Days: {day_count}", styles["body"])
    add_paragraph(story, f"Final sections: {final_count}", styles["body"])
    if render_document.route:
        add_paragraph(story, f"Route: {render_document.route}", styles["body"])
    add_paragraph(story, "Use this copy for internal review only. Confirm pictures, inclusions, exclusions, travel notes, and page breaks before sending the client PDF.", styles["editor_note"])
