"""Booknordics customer-brand CSS overrides for generated HTML previews."""

from ui.render_helpers import esc

_BRAND_SCOPE = '.preview-background[data-output-brand="booknordics_customer"]'


def _logo_rule(brand_logo_data_uri: str) -> str:
    if not brand_logo_data_uri:
        return ""
    return f'''
{_BRAND_SCOPE} .a4-page:not(.cover-page):not(.summary-page)::before {{
    content: "";
    position: absolute;
    top: 24px;
    right: 42px;
    width: 132px;
    height: 28px;
    background: url("{esc(brand_logo_data_uri)}") right center / contain no-repeat;
    z-index: 4;
}}
'''


def _page_and_cover_rules() -> str:
    return f'''
{_BRAND_SCOPE} .a4-page {{
    font-family: "DM Sans", sans-serif;
}}
{_BRAND_SCOPE} .cover-page {{
    background-color: var(--page-bg);
    background-size: cover !important;
    background-repeat: no-repeat !important;
}}
{_BRAND_SCOPE} .cover-main {{
    left: 72px;
    right: 72px;
    width: auto;
    max-width: none;
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    text-shadow: 0 2px 10px rgba(0,25,60,.28);
}}
{_BRAND_SCOPE} .cover-subtitle,
{_BRAND_SCOPE} .cover-destinations {{
    color: var(--cover-ink);
}}
{_BRAND_SCOPE} .cover-kicker,
{_BRAND_SCOPE} .cover-dates {{
    color: var(--cover-muted);
}}
{_BRAND_SCOPE} .cover-emblem {{
    border-color: rgba(255, 0, 65, .55);
}}
'''


def _font_rules() -> str:
    return f'''
{_BRAND_SCOPE} .cover-title,
{_BRAND_SCOPE} .cover-subtitle,
{_BRAND_SCOPE} .cover-dates,
{_BRAND_SCOPE} .cover-destinations,
{_BRAND_SCOPE} .day-title,
{_BRAND_SCOPE} .intro,
{_BRAND_SCOPE} .body-text,
{_BRAND_SCOPE} .editable-list,
{_BRAND_SCOPE} .detail-list,
{_BRAND_SCOPE} .final-list,
{_BRAND_SCOPE} .summary-title,
{_BRAND_SCOPE} .glance-title,
{_BRAND_SCOPE} .journey-title,
{_BRAND_SCOPE} .final-page-title {{
    font-family: "DM Sans", sans-serif;
}}
{_BRAND_SCOPE} .cover-title {{
    color: var(--cover-ink);
    font-weight: 700;
}}
{_BRAND_SCOPE} .day-title,
{_BRAND_SCOPE} .summary-title,
{_BRAND_SCOPE} .glance-title,
{_BRAND_SCOPE} .journey-title,
{_BRAND_SCOPE} .final-page-title {{
    color: var(--ink);
    font-weight: 700;
}}
'''


def _accent_rules() -> str:
    return f'''
{_BRAND_SCOPE} .cover-kicker,
{_BRAND_SCOPE} .cover-destination-label,
{_BRAND_SCOPE} .day-kicker,
{_BRAND_SCOPE} .page-kicker,
{_BRAND_SCOPE} .premium-note-card-title,
{_BRAND_SCOPE} .final-list-page .section-title,
{_BRAND_SCOPE} .categorized-inclusions-page .section-title,
{_BRAND_SCOPE} .categorized-exclusions-page .section-title,
{_BRAND_SCOPE} .premium-notes-page .section-title {{
    color: var(--accent);
    font-family: "DM Sans", sans-serif;
}}
{_BRAND_SCOPE} .day-page .section-title,
{_BRAND_SCOPE} .day-page .row-type,
{_BRAND_SCOPE} .day-page .ve-text-subheading {{
    color: var(--ink);
}}
{_BRAND_SCOPE} .cover-rule,
{_BRAND_SCOPE} .cover-rule::after {{
    background: var(--accent);
}}
{_BRAND_SCOPE} .day-kicker-symbol {{
    color: var(--accent);
}}
{_BRAND_SCOPE} .day-image-slot {{
    border-top-color: var(--accent);
}}
{_BRAND_SCOPE} .final-page-title::after,
{_BRAND_SCOPE} .glance-title::after,
{_BRAND_SCOPE} .journey-title::after {{
    background: var(--accent);
}}
'''


def _summary_rules() -> str:
    return f'''
{_BRAND_SCOPE} .summary-page {{
    background-image:
        linear-gradient(rgba(250,250,251,.58), rgba(250,250,251,.58)),
        var(--cover-bg-image);
    background-size: cover, cover;
    background-repeat: no-repeat, no-repeat;
}}
{_BRAND_SCOPE} .summary-page .glance-card,
{_BRAND_SCOPE} .summary-page .journey-arc,
{_BRAND_SCOPE} .premium-note-card {{
    background: rgba(255,255,255,.88);
    border-color: var(--line);
}}
'''


def build_booknordics_preview_overrides(brand_logo_data_uri: str) -> str:
    return "".join(
        (
            _logo_rule(brand_logo_data_uri),
            _page_and_cover_rules(),
            _font_rules(),
            _accent_rules(),
            _summary_rules(),
        )
    )
