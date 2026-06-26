"""Booknordics customer-brand CSS overrides for generated HTML previews."""

from ui.render_helpers import esc


def build_booknordics_preview_overrides(brand_logo_data_uri: str) -> str:
    logo_rule = ""
    if brand_logo_data_uri:
        logo_rule = f'''
.preview-background[data-output-brand="booknordics_customer"] .a4-page:not(.cover-page):not(.summary-page)::before {{
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
    return f'''
{logo_rule}
.preview-background[data-output-brand="booknordics_customer"] .a4-page {{
    font-family: "DM Sans", sans-serif;
}}
.preview-background[data-output-brand="booknordics_customer"] .cover-page {{
    background-color: var(--page-bg);
    background-size: cover !important;
    background-repeat: no-repeat !important;
}}
.preview-background[data-output-brand="booknordics_customer"] .cover-main {{
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
.preview-background[data-output-brand="booknordics_customer"] .cover-subtitle,
.preview-background[data-output-brand="booknordics_customer"] .cover-destinations {{
    color: var(--cover-ink);
}}
.preview-background[data-output-brand="booknordics_customer"] .cover-kicker,
.preview-background[data-output-brand="booknordics_customer"] .cover-dates {{
    color: var(--cover-muted);
}}

.preview-background[data-output-brand="booknordics_customer"] .cover-emblem {{
    border-color: rgba(255, 0, 65, .55);
}}
.preview-background[data-output-brand="booknordics_customer"] .cover-title,
.preview-background[data-output-brand="booknordics_customer"] .cover-subtitle,
.preview-background[data-output-brand="booknordics_customer"] .cover-dates,
.preview-background[data-output-brand="booknordics_customer"] .cover-destinations,
.preview-background[data-output-brand="booknordics_customer"] .day-title,
.preview-background[data-output-brand="booknordics_customer"] .intro,
.preview-background[data-output-brand="booknordics_customer"] .body-text,
.preview-background[data-output-brand="booknordics_customer"] .editable-list,
.preview-background[data-output-brand="booknordics_customer"] .detail-list,
.preview-background[data-output-brand="booknordics_customer"] .final-list,
.preview-background[data-output-brand="booknordics_customer"] .summary-title,
.preview-background[data-output-brand="booknordics_customer"] .glance-title,
.preview-background[data-output-brand="booknordics_customer"] .journey-title,
.preview-background[data-output-brand="booknordics_customer"] .final-page-title {{
    font-family: "DM Sans", sans-serif;
}}
.preview-background[data-output-brand="booknordics_customer"] .cover-title {{
    color: var(--cover-ink);
    font-weight: 700;
}}
.preview-background[data-output-brand="booknordics_customer"] .day-title,
.preview-background[data-output-brand="booknordics_customer"] .summary-title,
.preview-background[data-output-brand="booknordics_customer"] .glance-title,
.preview-background[data-output-brand="booknordics_customer"] .journey-title,
.preview-background[data-output-brand="booknordics_customer"] .final-page-title {{
    color: var(--ink);
    font-weight: 700;
}}
.preview-background[data-output-brand="booknordics_customer"] .cover-kicker,
.preview-background[data-output-brand="booknordics_customer"] .cover-destination-label,
.preview-background[data-output-brand="booknordics_customer"] .day-kicker,
.preview-background[data-output-brand="booknordics_customer"] .page-kicker,
.preview-background[data-output-brand="booknordics_customer"] .premium-note-card-title,
.preview-background[data-output-brand="booknordics_customer"] .final-list-page .section-title,
.preview-background[data-output-brand="booknordics_customer"] .categorized-inclusions-page .section-title,
.preview-background[data-output-brand="booknordics_customer"] .categorized-exclusions-page .section-title,
.preview-background[data-output-brand="booknordics_customer"] .premium-notes-page .section-title {{
    color: var(--accent);
    font-family: "DM Sans", sans-serif;
}}
.preview-background[data-output-brand="booknordics_customer"] .day-page .section-title,
.preview-background[data-output-brand="booknordics_customer"] .day-page .row-type,
.preview-background[data-output-brand="booknordics_customer"] .day-page .ve-text-subheading {{
    color: var(--ink);
}}
.preview-background[data-output-brand="booknordics_customer"] .cover-rule,
.preview-background[data-output-brand="booknordics_customer"] .cover-rule::after {{
    background: var(--accent);
}}
.preview-background[data-output-brand="booknordics_customer"] .day-kicker-symbol {{
    color: var(--accent);
}}
.preview-background[data-output-brand="booknordics_customer"] .day-image-slot {{
    border-top-color: var(--accent);
}}
.preview-background[data-output-brand="booknordics_customer"] .summary-page {{
    background-image:
        linear-gradient(rgba(250,250,251,.58), rgba(250,250,251,.58)),
        var(--cover-bg-image);
    background-size: cover, cover;
    background-repeat: no-repeat, no-repeat;
}}
.preview-background[data-output-brand="booknordics_customer"] .summary-page .glance-card,
.preview-background[data-output-brand="booknordics_customer"] .summary-page .journey-arc,
.preview-background[data-output-brand="booknordics_customer"] .premium-note-card {{
    background: rgba(255,255,255,.88);
    border-color: var(--line);
}}
.preview-background[data-output-brand="booknordics_customer"] .final-page-title::after,
.preview-background[data-output-brand="booknordics_customer"] .glance-title::after,
.preview-background[data-output-brand="booknordics_customer"] .journey-title::after {{
    background: var(--accent);
}}
'''
