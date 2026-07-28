"""Global Streamlit page chrome and shared component styles."""

BASE_CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
    overflow-y: auto !important;
    background: #f6f4ef !important;
    color: var(--ink) !important;
}

[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
[data-testid="stToolbar"], #MainMenu, footer { visibility: hidden !important; }

.block-container {
    max-width: min(calc(100% - 2rem), 1380px) !important;
    width: min(calc(100% - 2rem), 1380px) !important;
    padding: .75rem 0 3rem !important;
}

/* Pages are workspaces, not oversized decorative cards. */
.block-container:has(.studio-brand-link) {
    position: relative !important;
    overflow: visible !important;
    margin-top: 0 !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}

.block-container:has(.studio-brand-link)::before,
.block-container:has(.studio-brand-link)::after { content: none !important; display: none !important; }

h1, h2, h3, h4, h5, h6 { color: var(--ink) !important; letter-spacing: -.03em; }
p, li, label, [data-testid="stMarkdownContainer"] { color: var(--ink-soft) !important; }
label, [data-testid="stWidgetLabel"] p { color: var(--ink) !important; font-weight: 700 !important; }
div[data-testid="stHorizontalBlock"] { gap: .75rem !important; }

/* The application header is one quiet, aligned row. */
.st-key-input_top_actions,
.st-key-calculator_topbar,
.st-key-local_library_topbar {
    margin: 0 0 1.25rem !important;
    padding: .7rem 0 .9rem !important;
    border-bottom: 1px solid var(--line) !important;
}

@media (max-width: 740px) {
    .block-container {
        max-width: calc(100% - 1rem) !important;
        width: calc(100% - 1rem) !important;
        padding-top: .35rem !important;
    }
}
"""

STREAMLIT_COMPONENT_CSS = r"""
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}

[data-testid="stExpander"] {
    border-radius: 10px !important;
    border: 1px solid var(--line) !important;
    background: #fff !important;
    box-shadow: none !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] details,
[data-testid="stExpander"] summary { background: transparent !important; color: var(--ink) !important; }

[data-testid="stDialog"] > div {
    background: var(--paper) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    box-shadow: 0 20px 55px rgba(31, 38, 48, .14) !important;
}

[data-testid="stAlert"] {
    background: #fff !important;
    border: 1px solid var(--line) !important;
    border-left: 4px solid var(--accent) !important;
    border-radius: 10px !important;
    color: var(--ink) !important;
    box-shadow: none !important;
}
[data-testid="stAlert"] * { color: var(--ink) !important; }

iframe[title="visual_page_editor"] {
    border-radius: 12px !important;
    border: 1px solid var(--line) !important;
    box-shadow: none !important;
    background: var(--paper) !important;
}

.studio-brand-static { cursor: default !important; }
"""

CSS = "\n".join((BASE_CSS, STREAMLIT_COMPONENT_CSS))
