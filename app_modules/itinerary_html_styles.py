"""Aggregate preview/PDF HTML styles by responsibility."""

from app_modules.preview_css_cover import CSS as COVER_CSS
from app_modules.preview_css_day_pages import CSS as DAY_PAGE_CSS
from app_modules.preview_css_final_pages import CSS as FINAL_PAGE_CSS
from app_modules.preview_css_images import CSS as IMAGE_CSS
from app_modules.preview_css_responsive import CSS as RESPONSIVE_CSS
from app_modules.preview_css_summary import CSS as SUMMARY_CSS
from app_modules.preview_css_tokens import build_preview_tokens


def build_preview_style(colors, cover_theme, cover_background_data_uri):
    """Return the shared preview/PDF HTML style block."""

    sections = (
        build_preview_tokens(colors, cover_theme, cover_background_data_uri),
        COVER_CSS,
        SUMMARY_CSS,
        DAY_PAGE_CSS,
        FINAL_PAGE_CSS,
        IMAGE_CSS,
        RESPONSIVE_CSS,
    )
    css = "\n\n".join(section.strip() for section in sections if section.strip())
    return f"""
    <style>
        {css}
    </style>

"""
