import re

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from text_polish import expand_time_with_duration

from . import styles as pdf_styles
from .html_utils import clean_text, para_text
from .images import add_day_image_if_possible
from .story import add_bullets, add_paragraph, make_table


def render_cover_page(page, story, styles):
    story.append(Spacer(1, 95 * mm))
    add_paragraph(story, page.select_one(".cover-kicker").get_text(" ") if page.select_one(".cover-kicker") else "Curated Travel Itinerary", styles["cover_kicker"])
    add_paragraph(story, page.select_one(".cover-title").get_text(" ") if page.select_one(".cover-title") else "Itinerary", styles["cover_title"])
    add_paragraph(story, page.select_one(".cover-subtitle").get_text(" ") if page.select_one(".cover-subtitle") else "", styles["cover_subtitle"])
    add_paragraph(story, page.select_one(".cover-destinations").get_text(" ") if page.select_one(".cover-destinations") else "", styles["cover_destinations"])


def render_glance_page(page, story, styles):
    title = page.select_one(".glance-title")
    add_paragraph(story, title.get_text(" ") if title else "Your Trip at a Glance", styles["page_title"])

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
        story.append(make_table(rows, [38 * mm, 107 * mm], styles))
        story.append(Spacer(1, 14))

    journey_title = page.select_one(".journey-title")
    add_paragraph(story, journey_title.get_text(" ") if journey_title else "Your Journey Arc", styles["page_title"])

    table_rows = []
    header_cells = [clean_text(th.get_text(" ")) for th in page.select(".journey-table th")]
    if header_cells:
        table_rows.append([Paragraph(para_text(cell), styles["table_header"]) for cell in header_cells])

    for tr in page.select(".journey-table tbody tr"):
        cells = [clean_text(td.get_text(" ")) for td in tr.select("td")]
        if cells:
            table_rows.append([Paragraph(para_text(cell), styles["table_cell"]) for cell in cells])

    if table_rows:
        story.append(make_table(table_rows, [34 * mm, 22 * mm, 89 * mm], styles))


def _activity_time_range_text(time_text, duration_text):
    """PDF-side fallback: expand clean single start time + duration to a range."""
    cleaned_time = clean_text(time_text)
    base = re.sub(r"^time\s*:\s*", "", cleaned_time, flags=re.IGNORECASE).strip()
    expanded = expand_time_with_duration(base, duration_text)
    if expanded and expanded != base:
        return f"Time: {expanded}"
    return cleaned_time


def render_content_blocks(container, story, styles, compact=False, ultra=False):
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
                    add_paragraph(block_story, element.get_text(" "), styles["section_ultra" if ultra else ("section_compact" if compact else "section")])
                elif "activity-inclusion-title" in element_classes:
                    add_paragraph(block_story, element.get_text(" "), styles["activity_title"])
                elif element.name == "ul":
                    add_bullets(block_story, [li.get_text(" ") for li in element.find_all("li", recursive=False)], styles, compact=compact, ultra=ultra)
                elif "body-text" in element_classes:
                    text = clean_text(element.get_text(" "))
                    if "activity-block" in classes and re.match(r"^time\s*:", text, flags=re.IGNORECASE):
                        text = _activity_time_range_text(text, duration_meta_text)
                    if "strong-line" in element_classes:
                        add_paragraph(block_story, text, styles["body_bold_ultra" if ultra else ("body_bold_compact" if compact else "body_bold")])
                    else:
                        add_paragraph(block_story, text, styles["body_ultra" if ultra else ("body_compact" if compact else "body")])

            if "activity-block" in classes and block_story:
                story.append(KeepTogether(block_story))
            else:
                story.extend(block_story)


def add_day_separator(story, styles, ultra=False):
    story.append(Spacer(1, 4 if ultra else 6))
    table = Table([[""]], colWidths=[145 * mm], hAlign="LEFT")
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
    story.append(Spacer(1, 5 if ultra else 7))


def render_day_section_pdf(section, story, styles):
    classes = section.get("class") or []
    compact = "packed-section" in classes
    ultra = "triple-packed-section" in classes
    for selector, style_name in [
        (".day-label", "day_label"),
        (".day-title", "day_title"),
        (".city", "city"),
        (".intro", "intro"),
    ]:
        tag = section.select_one(selector)
        if tag:
            style_key = f"{style_name}_ultra" if ultra else (f"{style_name}_compact" if compact else style_name)
            add_paragraph(story, tag.get_text(" "), styles[style_key])

    render_content_blocks(section, story, styles, compact=compact, ultra=ultra)


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
            if index > 0:
                add_day_separator(story, styles, ultra="triple-packed-section" in (section.get("class") or []))
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

    render_content_blocks(page, story, styles)

    for ul in page.find_all("ul", recursive=False):
        add_bullets(story, [li.get_text(" ") for li in ul.find_all("li", recursive=False)], styles)

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
