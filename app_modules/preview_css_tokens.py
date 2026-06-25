"""Preview/PDF CSS tokens and base page styles."""

from app_modules.output_brand import BOOKNORDICS_BRAND, dm_sans_font_face_css
from app_modules.preview_css_brand_booknordics import build_booknordics_preview_overrides
from ui.render_helpers import esc


def build_preview_tokens(colors, cover_theme, cover_background_data_uri, *, output_brand="agent", brand_logo_data_uri=""):
    font_face_css = dm_sans_font_face_css(output_brand)
    document_font = "'DM Sans', sans-serif" if output_brand == BOOKNORDICS_BRAND else "Georgia, 'Times New Roman', serif"
    brand_overrides = build_booknordics_preview_overrides(brand_logo_data_uri) if output_brand == BOOKNORDICS_BRAND else ""
    return f"""
{font_face_css}
.preview-background {{
    --page-bg: {esc(colors['page_bg'])};
    --preview-bg: {esc(colors['preview_bg'])};
    --ink: {esc(colors['ink'])};
    --body: {esc(colors['body'])};
    --muted: {esc(colors['muted'])};
    --line: {esc(colors['line'])};
    --card: {esc(colors['card'])};
    --accent: {esc(colors['accent'])};
    --cover-ink: {esc(cover_theme['ink'])};
    --cover-muted: {esc(cover_theme['muted'])};
    --cover-accent: {esc(cover_theme['accent'])};
    --cover-bg-image: url("{esc(cover_background_data_uri)}");
    --document-font: {document_font};
    background: var(--preview-bg);
    padding: 32px 0 60px 0;
}}

.a4-page {{
    position: relative;
    width: 794px;
    min-height: 1123px;
    background: var(--page-bg);
    color: var(--ink);
    margin: 0 auto 32px auto;
    padding: 66px 64px;
    box-sizing: border-box;
    font-family: var(--document-font, Georgia, 'Times New Roman', serif);
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
    break-after: page;
    page-break-after: always;
    overflow: hidden;
}}
{brand_overrides}
"""
