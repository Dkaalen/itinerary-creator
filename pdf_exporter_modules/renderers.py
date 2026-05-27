import re

from reportlab.lib.units import mm
from reportlab.platypus import Flowable, KeepTogether, Paragraph, Spacer, Table, TableStyle

from text_polish import expand_time_with_duration

from . import styles as pdf_styles
from .html_utils import clean_text, para_text
from .images import FullPageBackgroundImage, FullPageTint, add_day_image_if_possible, resolve_image_path
from .story import add_bullets, add_paragraph, make_table


class CoverEmblem(Flowable):
    """Small centered circular cover emblem used by the PDF cover."""

    def __init__(self, size=15 * mm, color=None):
        super().__init__()
        self.width = float(size)
        self.height = float(size)
        self.color = color or pdf_styles.MUTED

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def split(self, availWidth, availHeight):
        return []

    def draw(self):
        canv = self.canv
        canv.saveState()
        canv.setStrokeColor(self.color)
        canv.setFillColor(self.color)
        canv.setLineWidth(0.45)
        radius = self.width / 2.0
        canv.circle(radius, radius, radius - 0.8, stroke=1, fill=0)
        canv.setFont("Times-Roman", 10)
        canv.drawCentredString(radius, radius - 3.2, "✦")
        canv.restoreState()


class CenterDiamondRule(Flowable):
    """Centered thin rule with a small diamond, matching the HTML cover accent."""

    def __init__(self, width=44 * mm, height=7 * mm, color=None):
        super().__init__()
        self.width = float(width)
        self.height = float(height)
        self.color = color or pdf_styles.MUTED

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def split(self, availWidth, availHeight):
        return []

    def draw(self):
        canv = self.canv
        y = self.height / 2.0
        canv.saveState()
        canv.setStrokeColor(self.color)
        canv.setFillColor(self.color)
        canv.setLineWidth(0.35)
        canv.line(0, y, self.width, y)
        diamond = 2.0
        x = self.width / 2.0
        path = canv.beginPath()
        path.moveTo(x, y + diamond)
        path.lineTo(x + diamond, y)
        path.lineTo(x, y - diamond)
        path.lineTo(x - diamond, y)
        path.close()
        canv.drawPath(path, stroke=0, fill=1)
        canv.restoreState()


def add_premium_rule(story, width=32 * mm, space_after=9):
    """Add a thin editorial accent rule below major headings."""
    table = Table([[""]], colWidths=[width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 0.45, pdf_styles.LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, space_after))


def add_cover_rule(story, width=44 * mm, space_after=9):
    table = Table([[CenterDiamondRule(width=width, color=pdf_styles.MUTED)]], colWidths=[width], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, space_after))


def _text_with_line_breaks(tag) -> str:
    if not tag:
        return ""
    parts = []
    for node in tag.descendants:
        name = getattr(node, "name", None)
        if name == "br":
            parts.append("\n")
        elif name is None:
            parts.append(str(node))
    text = "".join(parts).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _li_text_with_line_breaks(li) -> str:
    """Return list-item text while preserving explicit line structure.

    Some inclusion bullets are rendered as one <li> containing block children,
    for example a strong title div followed by one or more detail divs.
    BeautifulSoup's default text extraction joins those blocks together, so
    collect direct child blocks as separate lines before falling back to br-aware
    extraction for simpler list items.
    """
    direct_lines = []
    for child in li.find_all(recursive=False):
        line = clean_text(child.get_text(" "))
        if line:
            direct_lines.append(line)
    if direct_lines:
        return "\n".join(direct_lines)

    text = _text_with_line_breaks(li)
    return text or clean_text(li.get_text(" "))


def render_cover_page(page, story, styles, html_path=None, temp_dir=None):
    # Draw the static seasonal artwork first; all text remains editable/rendered.
    background_path = resolve_image_path(page.get("data-cover-background-path"), html_path) if html_path else None
    if background_path and temp_dir:
        story.append(FullPageBackgroundImage(background_path, temp_dir, crop_focus="top"))

    story.append(Spacer(1, 9 * mm))
    emblem = Table([[CoverEmblem(color=pdf_styles.MUTED)]], colWidths=[15 * mm], hAlign="CENTER")
    emblem.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(emblem)
    story.append(Spacer(1, 6 * mm))
    add_paragraph(story, page.select_one(".cover-kicker").get_text(" ") if page.select_one(".cover-kicker") else "Curated Travel Itinerary", styles["cover_kicker"])
    add_cover_rule(story, width=50 * mm, space_after=4)
    add_paragraph(story, page.select_one(".cover-title").get_text(" ") if page.select_one(".cover-title") else "Itinerary", styles["cover_title"])
    add_cover_rule(story, width=42 * mm, space_after=3)
    subtitle = _text_with_line_breaks(page.select_one(".cover-subtitle"))
    add_paragraph(story, subtitle, styles["cover_subtitle"])
    story.append(Spacer(1, 4 * mm))
    add_paragraph(story, "Route", styles["cover_route_label"])
    route_text = page.select_one(".cover-destinations").get_text(" ") if page.select_one(".cover-destinations") else ""
    add_paragraph(story, clean_text(route_text).upper(), styles["cover_destinations"])


def _boxed_story_table(flowables, width=160 * mm, padding=10, background=None):
    table = Table([[flowables]], colWidths=[width], hAlign="LEFT")
    card_background = background if background is not None else pdf_styles.CARD
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), card_background),
                ("BOX", (0, 0), (-1, -1), 0.5, pdf_styles.LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def add_soft_summary_background(page, story, html_path=None, temp_dir=None):
    """Add the seasonal artwork softly behind the summary page cards."""
    background_path = resolve_image_path(page.get("data-cover-background-path"), html_path) if html_path else None
    if background_path and temp_dir:
        story.append(FullPageBackgroundImage(background_path, temp_dir, crop_focus="top"))
        story.append(FullPageTint(color=pdf_styles.PAGE_BACKGROUND, alpha=0.38))


def render_glance_page(page, story, styles, html_path=None, temp_dir=None):
    add_soft_summary_background(page, story, html_path=html_path, temp_dir=temp_dir)

    glance_story = []
    title = page.select_one(".glance-title")
    add_paragraph(glance_story, title.get_text(" ") if title else "Your Trip at a Glance", styles["page_title"], spacer_after=6)

    rows = []
    for row in page.select(".glance-row"):
        label = row.select_one(".glance-label")
        value = row.select_one(".glance-value")
        if label and value:
            rows.append([
                Paragraph(para_text(label.get_text(" ")), styles["table_header"]),
                Paragraph(para_text(value.get_text(" ")), styles["table_cell"]),
            ])

    if rows:
        glance_story.append(make_table(rows, [34 * mm, 104 * mm], styles))

    story.append(_boxed_story_table(glance_story, background=pdf_styles.SUMMARY_CARD))
    story.append(Spacer(1, 16 * mm))

    journey_story = []
    journey_title = page.select_one(".journey-title")
    add_paragraph(journey_story, journey_title.get_text(" ") if journey_title else "Your Journey Arc", styles["page_title"], spacer_after=6)

    table_rows = []
    header_cells = [clean_text(th.get_text(" ")) for th in page.select(".journey-table th")]
    if header_cells:
        table_rows.append([Paragraph(para_text(cell), styles["table_header"]) for cell in header_cells])

    for tr in page.select(".journey-table tbody tr"):
        cells = [clean_text(td.get_text(" ")) for td in tr.select("td")]
        if cells:
            table_rows.append([Paragraph(para_text(cell), styles["table_cell"]) for cell in cells])

    if table_rows:
        journey_story.append(make_table(table_rows, [34 * mm, 16 * mm, 90 * mm], styles))

    story.append(_boxed_story_table(journey_story, background=pdf_styles.SUMMARY_CARD))


def _activity_time_range_text(time_text, duration_text):
    """PDF-side fallback: expand clean single start time + duration to a range."""
    cleaned_time = clean_text(time_text)
    base = re.sub(r"^time\s*:\s*", "", cleaned_time, flags=re.IGNORECASE).strip()
    expanded = expand_time_with_duration(base, duration_text)
    if expanded and expanded != base:
        return f"Time: {expanded}"
    return cleaned_time


def render_content_blocks(container, story, styles):
    for child in container.find_all(recursive=False):
        classes = child.get("class") or []
        if "content-block" in classes or "activity-inclusion-block" in classes:
            block_story = []

            duration_meta_text = ""
            if "activity-block" in classes:
                for possible_meta in child.find_all(recursive=False):
                    meta_text = clean_text(possible_meta.get_text(" "))
                    if re.match(r"^(?:duration|ferry duration|cruise duration)\s*:", meta_text, flags=re.IGNORECASE):
                        duration_meta_text = meta_text
                        break

            for element in child.find_all(recursive=False):
                element_classes = element.get("class") or []

                if "section-title" in element_classes:
                    add_paragraph(block_story, element.get_text(" "), styles["section"])
                elif "activity-inclusion-title" in element_classes:
                    add_paragraph(block_story, element.get_text(" "), styles["activity_title"])
                elif element.name == "ul":
                    add_bullets(block_story, [_li_text_with_line_breaks(li) for li in element.find_all("li", recursive=False)], styles)
                elif "body-text" in element_classes:
                    text = clean_text(element.get_text(" "))
                    if "activity-block" in classes and re.match(r"^time\s*:", text, flags=re.IGNORECASE):
                        text = _activity_time_range_text(text, duration_meta_text)
                    if "strong-line" in element_classes:
                        add_paragraph(block_story, text, styles["body_bold"])
                    else:
                        add_paragraph(block_story, text, styles["body"])

            if "activity-block" in classes and block_story:
                story.append(KeepTogether(block_story))
            else:
                story.extend(block_story)


def render_day_section_pdf(section, story, styles):
    for selector, style_name in [
        (".day-label", "day_label"),
        (".day-title", "day_title"),
        (".city", "city"),
        (".intro", "intro"),
    ]:
        tag = section.select_one(selector)
        if tag:
            add_paragraph(story, tag.get_text(" "), styles[style_name])

    render_content_blocks(section, story, styles)


def render_general_page(
    page,
    story,
    styles,
    html_path=None,
    temp_dir=None,
    available_width=None,
    available_height=None,
    left_margin=0,
    top_margin=0,
):
    page_story_start = len(story)

    day_sections = [child for child in page.find_all(recursive=False) if "day-section" in (child.get("class") or [])]
    if day_sections:
        for index, section in enumerate(day_sections):
            render_day_section_pdf(section, story, styles)
        if "day-page" in (page.get("class") or []) and html_path and temp_dir and available_width and available_height:
            add_day_image_if_possible(
                page,
                story,
                html_path,
                temp_dir,
                available_width,
                available_height,
                measurement_story=story[page_story_start:],
                left_margin=left_margin,
                top_margin=top_margin,
            )
        return

    for selector, style_name in [
        (".final-page-title", "page_title"),
        (".day-label", "day_label"),
        (".day-title", "day_title"),
        (".city", "city"),
        (".intro", "intro"),
    ]:
        tag = page.select_one(selector)
        if tag:
            add_paragraph(story, tag.get_text(" "), styles[style_name])
            if selector == ".final-page-title":
                add_premium_rule(story)

    render_content_blocks(page, story, styles)

    for ul in page.find_all("ul", recursive=False):
        add_bullets(story, [_li_text_with_line_breaks(li) for li in ul.find_all("li", recursive=False)], styles)

    if "day-page" in (page.get("class") or []) and html_path and temp_dir and available_width and available_height:
        add_day_image_if_possible(
            page,
            story,
            html_path,
            temp_dir,
            available_width,
            available_height,
            measurement_story=story[page_story_start:],
            left_margin=left_margin,
            top_margin=top_margin,
        )
