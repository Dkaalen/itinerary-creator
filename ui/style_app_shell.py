"""App shell, page chrome, and embedded editor frame styles."""

CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
    background: var(--app-bg) !important;
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
    max-width: min(100% - 4rem, 1120px) !important;
    width: min(100% - 4rem, 1120px) !important;
    padding: 2.35rem 0 4.4rem !important;
}

@media (max-width: 740px) {
    .block-container {
        max-width: min(100% - 1.25rem, 1120px) !important;
        width: min(100% - 1.25rem, 1120px) !important;
        padding-top: 1.2rem !important;
    }
}

h1, h2, h3, h4, h5, h6 {
    color: var(--ink) !important;
    letter-spacing: -0.045em;
}

p, li, label, [data-testid="stMarkdownContainer"] {
    color: var(--ink-soft) !important;
}

label, [data-testid="stWidgetLabel"] p {
    color: var(--ink) !important;
    font-weight: 720 !important;
}

div[data-testid="stHorizontalBlock"] {
    gap: .78rem !important;
}

/* Old marketing shell and status elements are intentionally not part of the product workspace. */
.luxury-hero,
.compact-app-header,
.hero-summary-card,
.flow-nav,
.document-stage-panel,
.app-version-pill,
.home-hero,
.home-hero-main,
.home-hero-side,
.home-section,
.workspace-help-card,
.workspace-tool-card,
.input-action-bar,
.calculator-hero,
.local-library-hero {
    display: none !important;
}

.workspace-shell {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin: 0 0 1.25rem;
    padding: .15rem 0 1rem;
    border-bottom: 1px solid rgba(224, 216, 202, 0.72);
}

.workspace-shell-main {
    min-width: 0;
    display: grid;
    gap: .12rem;
}

.workspace-shell-main strong {
    color: var(--ink) !important;
    font-size: 1rem;
    font-weight: 820;
    letter-spacing: -.025em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.workspace-shell-main span:not(.workspace-eyebrow) {
    color: var(--ink-soft) !important;
    font-size: .84rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.workspace-eyebrow,
.studio-wordmark,
.source-line span,
.calculator-kicker,
.local-library-kicker {
    color: var(--muted) !important;
    font-size: .68rem;
    font-weight: 850;
    letter-spacing: .14em;
    text-transform: uppercase;
}

.workspace-shell-meta {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: .52rem;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.workspace-shell-meta span {
    color: var(--ink-soft) !important;
    font-size: .76rem;
    font-weight: 680;
}

.workspace-shell-meta .workspace-action-chip {
    color: var(--ink) !important;
}

.studio-toolbar {
    display: flex;
    align-items: center;
    min-height: 2.42rem;
    margin: 0;
}

.input-page-heading,
.workspace-page-heading {
    margin: 2.35rem 0 1.2rem;
    max-width: 760px;
}

.workspace-page-heading {
    margin-top: 2rem;
}

.input-page-heading h1,
.workspace-page-heading h1 {
    color: var(--ink) !important;
    font-size: clamp(1.85rem, 3.2vw, 2.55rem);
    line-height: 1.06;
    letter-spacing: -.055em;
    margin: 0;
}

.source-line {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin: 1.5rem 0 .58rem;
}

.calculator-heading,
.local-library-heading {
    padding-bottom: .35rem;
}

.open-project-copy {
    display: grid;
    gap: .35rem;
    margin: .2rem 0 1rem;
}

.open-project-copy strong {
    color: var(--ink) !important;
    font-size: 1.08rem;
    letter-spacing: -.025em;
}

.open-project-copy span {
    color: var(--ink-soft) !important;
    font-size: .92rem;
    line-height: 1.45;
}

/* Streamlit native containers should not become a boxed app frame. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(224, 216, 202, 0.45) !important;
    border-radius: 16px !important;
    background: rgba(255, 253, 248, 0.48) !important;
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
    .workspace-shell {
        align-items: flex-start;
        flex-direction: column;
    }
}
"""
