"""Render editor-controlled paragraphs, lists, notes and dividers to PDF."""

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether

from . import styles as pdf_styles
from .html_utils import clean_text
from .render_flowables import add_premium_rule
from .render_text import li_text_with_line_breaks
from .story import add_bullets, add_paragraph
from visual_editor_component.style_presets import CONTROLLED_STYLE_CLASSES, pdf_base_style_for_classes, pdf_effects_for_classes

CONTROLLED_CLASSES = set(CONTROLLED_STYLE_CLASSES)


def class_set(element) -> set[str]:
    return {str(cls) for cls in (element.get("class") or [])}


def is_divider(element) -> bool:
    classes = class_set(element)
    return "ve-divider" in classes or "ve-divider-block" in classes


def has_controlled_classes(element) -> bool:
    return bool(class_set(element) & CONTROLLED_CLASSES)


def _registry_color(value):
    if value == "muted": return pdf_styles.MUTED
    if value == "accent": return pdf_styles.ACCENT
    if isinstance(value, str) and value.startswith("#"): return colors.HexColor(value)
    return None


def controlled_style(styles, classes, default_style_name="body"):
    style = styles[pdf_base_style_for_classes(classes, default_style_name)]
    values = {"text_color": None, "back_color": None, "space_after": None, "font_name": None, "font_size": None, "leading": None}
    suffix = []
    for effect in pdf_effects_for_classes(classes):
        for key, source in (("text_color", "pdf_text_color"), ("back_color", "pdf_back_color")):
            color = _registry_color(effect.get(source))
            if color is not None: values[key] = color
        for key, source in (("space_after", "pdf_space_after"), ("font_name", "pdf_font_name"), ("font_size", "pdf_font_size"), ("leading", "pdf_leading")):
            if effect.get(source) is not None: values[key] = effect[source]
        if effect.get("pdf_suffix"): suffix.append(str(effect["pdf_suffix"]))
    if not suffix: return style
    size = float(values["font_size"] or getattr(style, "fontSize", 10))
    kwargs = {"parent": style, "textColor": values["text_color"] or getattr(style, "textColor", pdf_styles.BODY), "fontName": values["font_name"] or getattr(style, "fontName", "Times-Roman"), "fontSize": size, "leading": float(values["leading"] or getattr(style, "leading", size * 1.35))}
    if values["back_color"] is not None: kwargs["backColor"] = values["back_color"]
    if values["space_after"] is not None: kwargs["spaceAfter"] = values["space_after"]
    return ParagraphStyle(f"{style.name}_{'_'.join(suffix)}", **kwargs)


def add_controlled_paragraph(story, element, styles, default_style_name="body"):
    text = clean_text(element.get_text(" "))
    if text: add_paragraph(story, text, controlled_style(styles, class_set(element), default_style_name))


def add_controlled_list(story, element, styles, *, spacer_after=7):
    items = element.find_all("li", recursive=False)
    if not items: return
    if not any(has_controlled_classes(item) for item in items):
        add_bullets(story, [li_text_with_line_breaks(item) for item in items], styles, spacer_after=spacer_after)
        return
    for item in items:
        text = li_text_with_line_breaks(item)
        if text: add_paragraph(story, f"• {text}", controlled_style(styles, class_set(item), "bullet"))


def render_controlled_note_block(child, story, styles):
    note_story = []
    for element in child.find_all(recursive=False):
        if is_divider(element): continue
        if element.name == "ul": add_controlled_list(note_story, element, styles)
        else: add_controlled_paragraph(note_story, element, styles, "editor_note")
    if not note_story:
        text = clean_text(child.get_text(" "))
        if text: add_paragraph(note_story, text, styles["editor_note"])
    if note_story: story.append(KeepTogether(note_story))


def render_divider(story):
    add_premium_rule(story, width=38 * mm, space_after=8)
