"""Final-section rendering for typed PDF export."""

from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Spacer

from itinerary_generation.render_model import RenderFinalPage, RenderFinalSection
from pdf_exporter_modules.render_flowables import add_premium_rule, boxed_story_table
from pdf_exporter_modules.pdf_supported_html_renderer import render_supported_html_fragment
from pdf_exporter_modules.story import add_bullets, add_paragraph
from ui.premium_final_notes import premium_note_cards


def render_supported_final_html(html_fragment: str, story, styles) -> None:
    render_supported_html_fragment(html_fragment, story, styles)


def render_final_page(title: str, page: RenderFinalPage, story, styles, *, continued=False):
    add_paragraph(story, title, styles["page_title"])
    add_premium_rule(story)
    if page.content_html:
        render_supported_final_html(page.content_html, story, styles)
        return
    for section in page.sections or []:
        add_paragraph(story, section.title, styles["section"])
        add_bullets(story, section.items, styles)
    if page.items:
        add_bullets(story, page.items, styles)
    for paragraph in page.paragraphs or []:
        add_paragraph(story, paragraph, styles["body"])


def render_important_notes_final_page(title: str, page: RenderFinalPage, story, styles):
    add_paragraph(story, title, styles["page_title"])
    add_premium_rule(story)
    cards = premium_note_cards(page.paragraphs or page.items or [])
    if not cards:
        for paragraph in page.paragraphs or []:
            add_paragraph(story, paragraph, styles["body"])
        return
    for card_title, body in cards:
        card_story = []
        add_paragraph(card_story, card_title, styles["section"])
        add_paragraph(card_story, body, styles["body"])
        story.append(KeepTogether([boxed_story_table(card_story, width=156 * mm, padding=7)]))
        story.append(Spacer(1, 5))


def render_final_section(section: RenderFinalSection, story, styles):
    pages = list(section.pages or [])
    if not pages:
        pages = [RenderFinalPage(sections=list(section.sections or []), items=list(section.items or []), paragraphs=list(section.paragraphs or []))]
    for index, page in enumerate(pages):
        if index > 0:
            story.append(PageBreak())
        if str(section.section_id or "") == "important_travel_notes" and not page.content_html:
            render_important_notes_final_page(section.title, page, story, styles)
        else:
            render_final_page(section.title, page, story, styles, continued=index > 0)
