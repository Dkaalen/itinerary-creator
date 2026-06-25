"""Summary-page rendering for typed PDF export."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer

from itinerary_generation.render_model import RenderDocument
from pdf_exporter_modules import styles as pdf_styles
from pdf_exporter_modules.html_utils import para_text
from pdf_exporter_modules.image_flowables import FullPageBackgroundImage, FullPageTint
from pdf_exporter_modules.render_flowables import boxed_story_table
from pdf_exporter_modules.story import add_paragraph, make_table


def render_summary(render_document: RenderDocument, story, styles, temp_dir):
    summary = render_document.summary
    if not summary:
        return
    background_path = Path(str(getattr(summary, "background_path", "") or ""))
    if background_path.exists() and background_path.is_file():
        story.append(FullPageBackgroundImage(background_path, temp_dir, crop_focus=getattr(summary, "crop_focus", "top")))
        story.append(FullPageTint(color=pdf_styles.PAGE_BACKGROUND, alpha=0.38))

    glance_story = []
    add_paragraph(glance_story, getattr(summary, "trip_glance_title", "") or "Your Trip at a Glance", styles["summary_title"], spacer_after=5)
    rows = []
    for line in getattr(summary, "trip_glance", []) or []:
        if line.label and line.value:
            rows.append([Paragraph(para_text(line.label), styles["summary_header"]), Paragraph(para_text(str(line.value)), styles["summary_cell"])])
    if rows:
        glance_story.append(make_table(rows, [34 * mm, 104 * mm], styles))
    story.append(boxed_story_table(glance_story, background=pdf_styles.SUMMARY_CARD))
    story.append(Spacer(1, 12 * mm))

    journey_story = []
    add_paragraph(journey_story, getattr(summary, "journey_arc_title", "") or "Your Journey Arc", styles["summary_title"], spacer_after=5)
    columns = getattr(summary, "journey_arc_columns", {}) or {}
    table_rows = [[Paragraph(para_text(str(columns.get("chapter") or "Chapter")), styles["summary_header"]), Paragraph(para_text(str(columns.get("days") or "Days")), styles["summary_header"]), Paragraph(para_text(str(columns.get("experience") or "What You’ll Experience")), styles["summary_header"])]]
    for row in getattr(summary, "journey_arc", []) or []:
        table_rows.append([
            Paragraph(para_text(str(row.get("chapter", ""))), styles["summary_cell"]),
            Paragraph(para_text(str(row.get("days", ""))), styles["summary_cell"]),
            Paragraph(para_text(str(row.get("experience", ""))), styles["summary_cell"]),
        ])
    if len(table_rows) > 1:
        journey_story.append(make_table(table_rows, [34 * mm, 16 * mm, 90 * mm], styles))
    story.append(boxed_story_table(journey_story, background=pdf_styles.SUMMARY_CARD))
