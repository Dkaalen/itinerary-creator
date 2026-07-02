"""App shell, page chrome, and embedded editor frame styles."""

CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(13, 111, 104, 0.055), transparent 34rem),
        linear-gradient(180deg, #fbf8f2 0%, var(--app-bg) 100%) !important;
    color: var(--ink) !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
}

[data-testid="stToolbar"],
#MainMenu,
footer {
    visibility: hidden !important;
}

.block-container {
    max-width: min(100% - 2.2rem, 1880px) !important;
    width: min(100% - 2.2rem, 1880px) !important;
    padding: 1.05rem 0 3.25rem !important;
}

@media (max-width: 740px) {
    .block-container {
        max-width: min(100% - 1rem, 1880px) !important;
        width: min(100% - 1rem, 1880px) !important;
        padding-top: .7rem !important;
    }
}

h1, h2, h3, h4, h5, h6 {
    color: var(--ink) !important;
    letter-spacing: -0.025em;
}

p, li, label, [data-testid="stMarkdownContainer"] {
    color: var(--ink-soft) !important;
}

label, [data-testid="stWidgetLabel"] p {
    color: var(--ink) !important;
    font-weight: 720 !important;
}

/* Old marketing shell and status elements are intentionally not part of the product workspace. */
.luxury-hero,
.compact-app-header,
.hero-summary-card,
.flow-nav,
.document-stage-panel,
.app-version-pill {
    display: none !important;
}

/* Streamlit containers become quiet work surfaces instead of high-contrast boxes. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--line) !important;
    border-radius: var(--radius-card) !important;
    background: rgba(255, 253, 250, 0.88) !important;
    box-shadow: var(--shadow-card) !important;
}

[data-testid="stExpander"] {
    border-radius: 14px !important;
    border: 1px solid var(--line) !important;
    background: rgba(255, 253, 250, 0.92) !important;
    box-shadow: none !important;
    overflow: hidden !important;
}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary {
    background: transparent !important;
    color: var(--ink) !important;
}

[data-testid="stAlert"] {
    background: #fffaf0 !important;
    border: 1px solid #ecd9b8 !important;
    border-left: 4px solid var(--warning) !important;
    border-radius: 14px !important;
    color: var(--ink) !important;
    box-shadow: none !important;
}

[data-testid="stAlert"] * {
    color: var(--ink) !important;
}

iframe[title="visual_page_editor"] {
    border-radius: 18px !important;
    border: 1px solid var(--line) !important;
    box-shadow: var(--shadow-soft) !important;
    background: var(--paper) !important;
}
"""
