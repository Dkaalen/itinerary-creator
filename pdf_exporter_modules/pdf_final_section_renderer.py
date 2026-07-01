"""Final-section rendering for typed PDF export."""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Spacer

from itinerary_generation.render_model import RenderFinalPage, RenderFinalSection
from pdf_exporter_modules.html_utils import clean_text
from pdf_exporter_modules.render_content import render_content_blocks
from pdf_exporter_modules.render_flowables import add_premium_rule, boxed_story_table
from pdf_exporter_modules.render_text import li_text_with_line_breaks
from pdf_exporter_modules.story import add_bullets, add_paragraph
from ui.premium_final_notes import premium_note_cards


def render_supported_final_html(html_fragment: str, story, styles) -> None:
    html_fragment = str(html_fragment or "").strip()
    if not html_fragment:
        return

    soup = BeautifulSoup(html_fragment, "html.parser")

    def render_children(container):
        for child in getattr(container, "contents", []):
            if isinstance(child, NavigableString):
                text = clean_text(str(child))
                if text:
                    add_paragraph(story, text, styles["body"])
                continue
            if not getattr(child, "name", None):
                continue

            classes = child.get("class") or []
            if "content-block" in classes or "activity-inclusion-block" in classes:
                render_content_blocks(BeautifulSoup(str(child), "html.parser"), story, styles)
                continue

            if child.name in {"ul", "ol"}:
                add_bullets(story, [li_text_with_line_breaks(li) for li in child.find_all("li", recursive=False)], styles)
                continue

            if "section-title" in classes:
                add_paragraph(story, child.get_text(" "), styles["section"])
                continue

            if child.name in {"strong", "b"}:
                add_paragraph(story, child.get_text(" "), styles["body_bold"])
                continue

            if child.name in {"p", "span", "div", "em", "i"}:
                nested_structures = child.find_all(["ul", "ol"], recursive=False) or child.find_all(class_="content-block", recursive=False)
                if nested_structures:
                    render_children(child)
                    continue
                text = clean_text(child.get_text(" "))
                if text:
                    style_name = "body_bold" if "strong-line" in classes else "body"
                    add_paragraph(story, text, styles[style_name])

    render_children(soup)


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
