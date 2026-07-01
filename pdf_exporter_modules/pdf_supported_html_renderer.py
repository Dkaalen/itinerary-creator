"""Render typed-PDF-safe editor HTML fragments."""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString

from pdf_exporter_modules.html_utils import clean_text
from pdf_exporter_modules.render_content import render_content_blocks
from pdf_exporter_modules.render_text import li_text_with_line_breaks
from pdf_exporter_modules.story import add_bullets, add_paragraph


def render_supported_html_fragment(html_fragment: str, story, styles) -> None:
    """Append flowables for HTML already accepted by pdf_html_support."""

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


__all__ = ["render_supported_html_fragment"]
