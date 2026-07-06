"""App shell, page chrome, and embedded editor frame styles."""

CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 12% -10%, rgba(15, 106, 95, 0.10), transparent 32rem),
        radial-gradient(circle at 92% 4%, rgba(232, 223, 207, 0.55), transparent 30rem),
        linear-gradient(180deg, #fbfaf6 0%, var(--app-bg) 100%) !important;
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
    max-width: min(100% - 2.6rem, 1880px) !important;
    width: min(100% - 2.6rem, 1880px) !important;
    padding: 1rem 0 3.5rem !important;
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
    letter-spacing: -0.035em;
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

.workspace-shell {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin: .15rem 0 .9rem;
    padding: .82rem .95rem;
    border: 1px solid rgba(199, 208, 202, 0.72);
    border-radius: 20px;
    background: rgba(255, 253, 248, 0.72);
    box-shadow: var(--shadow-control);
    backdrop-filter: blur(10px);
}

.workspace-shell-main {
    min-width: 0;
    display: grid;
    gap: .12rem;
}

.workspace-shell-main strong {
    color: var(--ink) !important;
    font-size: 1.02rem;
    font-weight: 880;
    letter-spacing: -.018em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.workspace-shell-main span:not(.workspace-eyebrow) {
    color: var(--ink-soft) !important;
    font-size: .88rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.workspace-eyebrow {
    color: var(--teal-dark) !important;
    font-size: .68rem;
    font-weight: 900;
    letter-spacing: .13em;
    text-transform: uppercase;
}

.workspace-shell-meta {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: .45rem;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.workspace-shell-meta span {
    color: var(--ink-soft) !important;
    font-size: .76rem;
    font-weight: 760;
    border: 1px solid rgba(199, 208, 202, .70);
    background: rgba(248, 245, 238, .82);
    border-radius: 999px;
    padding: .28rem .52rem;
}

.workspace-shell-meta .workspace-action-chip {
    color: var(--teal-dark) !important;
    border-color: rgba(15, 106, 95, .26);
    background: rgba(233, 244, 241, .92);
}

/* Streamlit containers become quiet work surfaces instead of high-contrast boxes. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(199, 208, 202, 0.72) !important;
    border-radius: var(--radius-card) !important;
    background: rgba(255, 253, 248, 0.82) !important;
    box-shadow: var(--shadow-card) !important;
    backdrop-filter: blur(10px) !important;
}

[data-testid="stExpander"] {
    border-radius: 18px !important;
    border: 1px solid rgba(199, 208, 202, 0.76) !important;
    background: rgba(255, 253, 248, 0.82) !important;
    box-shadow: var(--shadow-control) !important;
    overflow: hidden !important;
}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary {
    background: transparent !important;
    color: var(--ink) !important;
}

[data-testid="stAlert"] {
    background: rgba(255, 253, 248, 0.92) !important;
    border: 1px solid rgba(199, 208, 202, 0.80) !important;
    border-left: 3px solid var(--teal) !important;
    border-radius: 16px !important;
    color: var(--ink) !important;
    box-shadow: var(--shadow-control) !important;
}

[data-testid="stAlert"] * {
    color: var(--ink) !important;
}

iframe[title="visual_page_editor"] {
    border-radius: 22px !important;
    border: 1px solid rgba(199, 208, 202, 0.80) !important;
    box-shadow: var(--shadow-soft) !important;
    background: var(--paper) !important;
}
"""
