"""App shell, header, and embedded editor frame styles."""

CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
    background: var(--app-bg) !important;
    color: var(--ink) !important;
}

.block-container {
    max-width: none;
    width: 100%;
    padding: 0.85rem 1.15rem 3.25rem;
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
    font-weight: 760 !important;
}

.luxury-hero,
.compact-app-header,
.hero-summary-card,
.flow-nav {
    display: none !important;
}

.app-version-pill { display: none !important; }

/* Remove Streamlit's dark focus/corner artifacts around rounded inputs. */
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    outline: none !important;
}

[data-baseweb="input"],
[data-baseweb="textarea"],
[data-baseweb="select"] {
    background: transparent !important;
}
"""
