from .exporter import export_html_to_pdf
from .export_profiles import pdf_export_profile_options, pdf_filename, resolve_pdf_export_profile
from .typed_exporter import export_render_document_to_pdf, render_document_requires_html_fallback
from .html_utils import clean_text, has_class, para_text
from .images import (
    PDF_CROP_FOCUS_FACTORS,
    PDF_CROP_VERTICAL_FOCUS,
    PDF_IMAGE_BOTTOM_Y,
    PDF_IMAGE_GAP,
    PDF_IMAGE_HALF_OFFSET,
    PDF_MIN_IMAGE_HEIGHT,
    SamePageDayImage,
    add_day_image_if_possible,
    calculate_day_image_layout,
    make_cover_cropped_image,
    normalize_crop_focus,
    resolve_image_path,
)
from .renderers import (
    _activity_time_range_text,
    render_content_blocks,
    render_cover_page,
    render_day_section_pdf,
    render_general_page,
    render_glance_page,
)
from .story import add_bullets, add_paragraph, make_table, story_height
from .styles import (
    BODY,
    CARD,
    DEFAULT_PDF_COLORS,
    INK,
    LINE,
    MUTED,
    PAGE_BACKGROUND,
    apply_pdf_palette,
    extract_pdf_palette,
    hex_to_color,
    make_styles,
    page_background,
)

__all__ = [name for name in globals() if not name.startswith("_")]
