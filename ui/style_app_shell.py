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
    max-width: min(100% - 4rem, 1180px) !important;
    width: min(100% - 4rem, 1180px) !important;
    padding: 2rem 0 4rem !important;
}

@media (max-width: 740px) {
    .block-container {
        max-width: min(100% - 1.25rem, 1180px) !important;
        width: min(100% - 1.25rem, 1180px) !important;
        padding-top: 1rem !important;
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
.input-action-bar {
    display: none !important;
}

.workspace-shell {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin: 0 0 1.4rem;
    padding: .68rem 0 .9rem;
    border-bottom: 1px solid var(--line);
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
.generate-line span,
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

/* Input page: quiet workspace, not a landing page or card dashboard. */
.studio-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
    margin: .1rem 0 .9rem;
    padding-bottom: .72rem;
    border-bottom: 1px solid var(--line);
}

.studio-toolbar-note {
    color: var(--muted) !important;
    font-size: .82rem;
    margin-left: .65rem;
}

.input-page-heading {
    margin: 2.05rem 0 1.2rem;
    max-width: 760px;
}

.input-page-heading h1 {
    color: var(--ink) !important;
    font-size: clamp(2rem, 4vw, 3.3rem);
    line-height: 1.02;
    letter-spacing: -.065em;
    margin: 0 0 .55rem;
}

.input-page-heading p {
    color: var(--ink-soft) !important;
    font-size: 1rem;
    line-height: 1.62;
    margin: 0;
    max-width: 680px;
}

.source-line {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin: 1.55rem 0 .62rem;
}

.source-line small {
    color: var(--muted) !important;
    font-size: .82rem;
}

.generate-line {
    margin: 1.05rem 0 .58rem;
    padding-top: .2rem;
}

.calculator-hero,
.local-library-hero {
    padding: .2rem 0 1rem;
    margin: .2rem 0 .55rem;
    border-bottom: 1px solid var(--line);
}

.calculator-title,
.local-library-title {
    color: var(--ink) !important;
    font-size: clamp(1.8rem, 3vw, 2.8rem);
    line-height: 1.04;
    letter-spacing: -.06em;
    margin: .25rem 0 .45rem;
}

.calculator-description,
.local-library-description {
    color: var(--ink-soft) !important;
    font-size: .96rem;
    line-height: 1.62;
    margin: 0;
    max-width: 720px;
}

.calculator-top-strip {
    display: grid;
    grid-template-columns: minmax(120px, .18fr) minmax(180px, .22fr) minmax(0, 1fr);
    gap: .58rem;
    align-items: center;
    margin: .65rem 0 .85rem;
}

.calculator-status-caption {
    color: var(--muted) !important;
    font-size: .82rem;
    text-align: right;
}

/* Streamlit native containers should not look like scattered boxed dashboards. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--line) !important;
    border-radius: 18px !important;
    background: rgba(255, 253, 248, 0.70) !important;
    box-shadow: none !important;
}

[data-testid="stExpander"] {
    border-radius: 14px !important;
    border: 1px solid var(--line) !important;
    background: rgba(255, 253, 248, 0.64) !important;
    box-shadow: none !important;
    overflow: hidden !important;
}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary {
    background: transparent !important;
    color: var(--ink) !important;
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
    border: 1px solid var(--line) !important;
    box-shadow: 0 18px 46px rgba(36, 37, 34, 0.06) !important;
    background: var(--paper) !important;
}

@media (max-width: 980px) {
    .calculator-top-strip {
        grid-template-columns: 1fr;
    }
    .calculator-status-caption {
        text-align: left;
    }
    .workspace-shell,
    .studio-toolbar,
    .source-line {
        align-items: flex-start;
        flex-direction: column;
    }
}
"""
