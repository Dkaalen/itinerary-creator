from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.platypus import KeepTogether, Paragraph, Table

from pdf_exporter_modules.render_content import render_content_blocks
from pdf_exporter_modules.styles import make_styles
from ui.editor_sanitizer import clean_visual_editor_html


def test_patch_bl_sidebar_exposes_controlled_presets_not_freeform_styles():
    inspector_js = (
        open("visual_editor_component/frontend/js/editor_inspector.js", encoding="utf-8").read()
        + "\n"
        + open("visual_editor_component/frontend/js/editor_inspector_text_panel.js", encoding="utf-8").read()
    )
    style_presets_js = open("visual_editor_component/frontend/js/style_presets.js", encoding="utf-8").read()
    commands_js = open("visual_editor_component/frontend/js/commands.js", encoding="utf-8").read()

    assert "Font" in inspector_js
    assert "Size" in inspector_js
    assert "Text color / highlight" in inspector_js
    assert "Small note" in style_presets_js
    assert "Accent gold" in style_presets_js
    assert "Georgia" in style_presets_js
    assert "12 pt" in style_presets_js
    assert 'input type="color"' not in inspector_js
    assert "style.fontSize" not in commands_js
    assert "style.color" not in commands_js


def test_patch_bl_sanitizer_preserves_controlled_classes_but_removes_inline_styles():
    html = (
        '<div class="content-block ve-note-block" style="color:red" onclick="bad()">'
        '<div class="body-text ve-text-small-note ve-color-highlight">Helpful note</div>'
        '</div>'
    )

    cleaned = clean_visual_editor_html(html)

    assert "ve-note-block" in cleaned
    assert "ve-text-small-note" in cleaned
    assert "ve-color-highlight" in cleaned
    assert "style=" not in cleaned
    assert "onclick" not in cleaned


def test_patch_bl_pdf_renders_controlled_text_presets():
    soup = BeautifulSoup(
        '<div class="content-block">'
        '<div class="body-text ve-text-heading ve-color-accent">Styled heading</div>'
        '<div class="body-text ve-text-small-note ve-color-muted">Small note</div>'
        '</div>',
        "html.parser",
    )
    story = []

    render_content_blocks(soup, story, make_styles())

    paragraphs = [item for item in story if isinstance(item, Paragraph)]
    assert len(paragraphs) == 2
    assert paragraphs[0].style.name.startswith("editor_heading")
    assert paragraphs[0].style.textColor == colors.HexColor("#9a6a16")
    assert paragraphs[1].style.name.startswith("editor_small_note")


def test_patch_bl_pdf_renders_note_and_divider_blocks():
    soup = BeautifulSoup(
        '<div class="content-block ve-note-block"><div class="body-text">Remember passport.</div></div>'
        '<div class="content-block ve-divider-block"><div class="ve-divider">&nbsp;</div></div>',
        "html.parser",
    )
    story = []

    render_content_blocks(soup, story, make_styles())

    assert any(isinstance(item, KeepTogether) for item in story)
    assert any(isinstance(item, Table) for item in story)


def test_ui18_pdf_renders_controlled_font_and_size_presets():
    soup = BeautifulSoup(
        '<div class="content-block">'
        '<div class="body-text ve-font-arial ve-size-14 ve-color-warning">Styled copy</div>'
        '</div>',
        "html.parser",
    )
    story = []

    render_content_blocks(soup, story, make_styles())

    paragraphs = [item for item in story if isinstance(item, Paragraph)]
    assert len(paragraphs) == 1
    assert paragraphs[0].style.fontName == "Helvetica"
    assert paragraphs[0].style.fontSize == 14
    assert paragraphs[0].style.textColor == colors.HexColor("#7a1c1c")
