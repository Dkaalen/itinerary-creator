"""App shell, page chrome, and embedded editor frame styles."""

CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 14% -12%, rgba(129, 119, 105, 0.12), transparent 30rem),
        radial-gradient(circle at 92% 2%, rgba(232, 223, 207, 0.46), transparent 34rem),
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
    max-width: min(100% - 3.2rem, 1440px) !important;
    width: min(100% - 3.2rem, 1440px) !important;
    padding: 1.05rem 0 3.5rem !important;
}

@media (max-width: 740px) {
    .block-container {
        max-width: min(100% - 1rem, 1440px) !important;
        width: min(100% - 1rem, 1440px) !important;
        padding-top: .7rem !important;
    }
}

h1, h2, h3, h4, h5, h6 {
    color: var(--ink) !important;
    letter-spacing: -0.04em;
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
    margin: .15rem 0 1rem;
    padding: .78rem .92rem;
    border: 1px solid rgba(207, 198, 183, 0.76);
    border-radius: 22px;
    background: rgba(255, 253, 248, 0.74);
    box-shadow: var(--shadow-control);
    backdrop-filter: blur(12px);
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
    letter-spacing: -.025em;
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
    color: var(--accent-dark) !important;
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
    border: 1px solid rgba(207, 198, 183, .74);
    background: rgba(247, 243, 235, .84);
    border-radius: 999px;
    padding: .28rem .52rem;
}

.workspace-shell-meta .workspace-action-chip {
    color: var(--ink) !important;
    border-color: rgba(47, 48, 45, .22);
    background: rgba(239, 235, 226, .95);
}

/* Input page and workspace composition. */
.home-hero {
    display: grid;
    grid-template-columns: minmax(0, 1.3fr) minmax(260px, .7fr);
    gap: 1rem;
    align-items: stretch;
    margin: .2rem 0 1.1rem;
}

.home-hero-main,
.home-hero-side,
.home-section,
.workspace-tool-card,
.workspace-help-card,
.local-library-hero,
.calculator-hero {
    border: 1px solid rgba(207, 198, 183, .76);
    border-radius: 28px;
    background: rgba(255, 253, 248, .78);
    box-shadow: var(--shadow-card);
    backdrop-filter: blur(12px);
}

.home-hero-main {
    padding: 1.35rem 1.45rem;
}

.home-hero-side {
    padding: 1.05rem;
    display: grid;
    align-content: start;
    gap: .72rem;
}

.home-kicker,
.section-kicker,
.calculator-kicker,
.local-library-kicker {
    display: inline-flex;
    color: var(--accent-dark) !important;
    font-size: .68rem;
    font-weight: 900;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin-bottom: .32rem;
}

.home-title {
    color: var(--ink) !important;
    font-size: clamp(2.1rem, 4vw, 4.4rem);
    line-height: .96;
    letter-spacing: -.075em;
    margin: .1rem 0 .7rem;
    max-width: 13ch;
}

.home-description,
.section-description,
.tool-card-description,
.calculator-description,
.local-library-description {
    color: var(--ink-soft) !important;
    font-size: .98rem;
    line-height: 1.62;
    margin: 0;
}

.home-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: .45rem;
    margin-top: 1.05rem;
}

.home-meta-row span,
.section-chip,
.tool-chip {
    display: inline-flex;
    align-items: center;
    border: 1px solid rgba(207, 198, 183, .78);
    background: rgba(247, 243, 235, .88);
    color: var(--ink-soft) !important;
    border-radius: 999px;
    padding: .32rem .58rem;
    font-size: .76rem;
    font-weight: 760;
}

.home-section {
    padding: 1.08rem 1.12rem;
    margin: .8rem 0;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: .72rem;
}

.section-title {
    color: var(--ink) !important;
    font-size: 1.18rem;
    line-height: 1.05;
    letter-spacing: -.04em;
    font-weight: 900;
    margin: 0;
}

.workspace-tool-card,
.workspace-help-card {
    padding: .92rem;
    border-radius: 22px;
    box-shadow: var(--shadow-control);
}

.tool-card-title {
    display: block;
    color: var(--ink) !important;
    font-weight: 900;
    letter-spacing: -.025em;
    margin-bottom: .14rem;
}

.home-action-note {
    color: var(--muted) !important;
    font-size: .82rem;
    margin: .6rem 0 0;
}

.input-action-bar {
    margin: .9rem 0 .55rem;
    padding: .82rem .95rem;
    border: 1px solid rgba(207, 198, 183, .76);
    border-radius: 24px;
    background: rgba(255, 253, 248, .82);
    box-shadow: var(--shadow-card);
}

.input-action-copy strong {
    display: block;
    color: var(--ink) !important;
    font-size: .98rem;
    font-weight: 900;
}

.input-action-copy span {
    color: var(--ink-soft) !important;
    display: block;
    font-size: .86rem;
    margin-top: .08rem;
}

.calculator-hero,
.local-library-hero {
    padding: 1rem 1.08rem;
    margin: .2rem 0 1rem;
}

.calculator-title,
.local-library-title {
    color: var(--ink) !important;
    font-size: clamp(1.75rem, 3vw, 3rem);
    line-height: 1;
    letter-spacing: -.065em;
    margin: .12rem 0 .45rem;
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

/* Streamlit containers become quiet work surfaces instead of high-contrast boxes. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(207, 198, 183, 0.76) !important;
    border-radius: var(--radius-card) !important;
    background: rgba(255, 253, 248, 0.80) !important;
    box-shadow: var(--shadow-card) !important;
    backdrop-filter: blur(10px) !important;
}

[data-testid="stExpander"] {
    border-radius: 18px !important;
    border: 1px solid rgba(207, 198, 183, 0.78) !important;
    background: rgba(255, 253, 248, 0.80) !important;
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
    border: 1px solid rgba(207, 198, 183, 0.82) !important;
    border-left: 3px solid var(--accent) !important;
    border-radius: 16px !important;
    color: var(--ink) !important;
    box-shadow: var(--shadow-control) !important;
}

[data-testid="stAlert"] * {
    color: var(--ink) !important;
}

iframe[title="visual_page_editor"] {
    border-radius: 22px !important;
    border: 1px solid rgba(207, 198, 183, 0.82) !important;
    box-shadow: var(--shadow-soft) !important;
    background: var(--paper) !important;
}

@media (max-width: 980px) {
    .home-hero,
    .input-action-bar,
    .calculator-top-strip {
        grid-template-columns: 1fr;
    }
    .calculator-status-caption {
        text-align: left;
    }
}
"""
