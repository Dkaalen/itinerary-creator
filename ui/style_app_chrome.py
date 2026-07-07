"""Global Streamlit page chrome and shared Streamlit component styles."""

BASE_CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
    overflow-y: auto !important;
    background:
        radial-gradient(circle at 18% 0%, rgba(255, 253, 248, 0.82) 0, rgba(255, 253, 248, 0) 31rem),
        linear-gradient(180deg, #f7f4ee 0%, var(--app-bg) 100%) !important;
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
    max-width: min(calc(100% - 3rem), 1480px) !important;
    width: min(calc(100% - 3rem), 1480px) !important;
    padding: 0 0 4.2rem !important;
}

.block-container:has(.studio-brand-link) {
    position: relative !important;
    overflow: visible !important;
    margin-top: 1.15rem !important;
    background:
        linear-gradient(180deg, rgba(255, 253, 248, 0.97) 0%, rgba(255, 253, 248, 0.93) 100%) !important;
    border: 1px solid rgba(218, 209, 196, 0.86) !important;
    border-radius: 14px !important;
    box-shadow: var(--shadow-soft) !important;
}

.block-container:has(.input-page-heading)::before {
    content: "";
    position: absolute;
    inset: auto 0 0 auto;
    width: min(38rem, 42%);
    height: 10rem;
    pointer-events: none;
    z-index: 0;
    opacity: .55;
    background:
        linear-gradient(135deg, transparent 0 34%, rgba(111, 128, 137, .18) 34.5% 45%, transparent 45.5%),
        linear-gradient(152deg, transparent 0 48%, rgba(111, 128, 137, .28) 48.5% 63%, transparent 63.5%),
        linear-gradient(170deg, transparent 0 61%, rgba(111, 128, 137, .42) 61.5% 75%, transparent 75.5%);
}

.block-container:has(.input-page-heading)::after {
    content: "";
    position: absolute;
    left: 0;
    bottom: 0;
    width: 28rem;
    height: 8rem;
    pointer-events: none;
    z-index: 0;
    opacity: .20;
    background:
        repeating-radial-gradient(ellipse at 0% 100%, transparent 0 11px, rgba(168, 153, 134, .34) 12px 13px, transparent 14px 25px);
}

.block-container:has(.studio-brand-link) > div {
    position: relative;
    z-index: 1;
}

@media (max-width: 740px) {
    .block-container {
        max-width: min(calc(100% - 1rem), 1480px) !important;
        width: min(calc(100% - 1rem), 1480px) !important;
    }

    .block-container:has(.studio-brand-link) {
        margin-top: .6rem !important;
        border-radius: 12px !important;
    }
}

h1, h2, h3, h4, h5, h6 {
    color: var(--ink) !important;
    letter-spacing: -0.035em;
}

p, li, label, [data-testid="stMarkdownContainer"] {
    color: var(--ink-soft) !important;
}

label, [data-testid="stWidgetLabel"] p {
    color: var(--ink) !important;
    font-weight: 740 !important;
}

div[data-testid="stHorizontalBlock"] {
    gap: .9rem !important;
}

"""

STREAMLIT_COMPONENT_CSS = r"""/* Do not let Streamlit border wrappers recreate the trapped outer app frame. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}

[data-testid="stExpander"] {
    border-radius: 14px !important;
    border: 1px solid rgba(224, 216, 202, 0.68) !important;
    background: rgba(255, 253, 248, 0.50) !important;
    box-shadow: none !important;
    overflow: hidden !important;
}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary {
    background: transparent !important;
    color: var(--ink) !important;
}

[data-testid="stDialog"] > div {
    background: var(--paper) !important;
    border: 1px solid rgba(224, 216, 202, 0.86) !important;
    border-radius: 20px !important;
    box-shadow: 0 24px 70px rgba(36, 37, 34, 0.14) !important;
}

[data-testid="stAlert"] {
    background: rgba(255, 253, 248, 0.90) !important;
    border: 1px solid var(--line) !important;
    border-left: 3px solid var(--accent) !important;
    border-radius: 14px !important;
    color: var(--ink) !important;
    box-shadow: none !important;
}

[data-testid="stAlert"] * {
    color: var(--ink) !important;
}

iframe[title="visual_page_editor"] {
    border-radius: 18px !important;
    border: 1px solid rgba(224, 216, 202, 0.76) !important;
    box-shadow: none !important;
    background: var(--paper) !important;
}

@media (max-width: 980px) {
    .workspace-shell,
    div[data-testid="stHorizontalBlock"]:has(.studio-brand-link) {
        align-items: stretch !important;
        flex-direction: column;
    }

    div[data-testid="stHorizontalBlock"]:has(.studio-brand-link) {
        display: grid !important;
        grid-template-columns: 1fr !important;
    }
}

.studio-brand-static {
    cursor: default !important;
}

"""

CSS = "\n".join(
    (
    BASE_CSS,
    STREAMLIT_COMPONENT_CSS,
    )
)
