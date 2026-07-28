"""Workspace shell, hidden legacy chrome, and Booknordics brand header styles."""

CSS = r"""/* Old marketing shell and status elements are intentionally not part of the product workspace. */
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
.source-line span,
.calculator-kicker,
.local-library-kicker,
.input-page-kicker {
    color: var(--muted) !important;
    font-size: .72rem;
    font-weight: 880;
    letter-spacing: .18em;
    text-transform: uppercase;
}

.input-page-kicker {
    display: inline-block;
    color: var(--red-dark) !important;
    margin-bottom: .35rem;
    position: relative;
}

.input-page-kicker::after {
    content: "";
    display: block;
    width: 2rem;
    height: 2px;
    margin-top: .35rem;
    background: var(--red-dark);
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

/* Concept-matched top workspace bar. */
div[data-testid="stHorizontalBlock"]:has(.studio-brand-link) {
    align-items: center !important;
    gap: .9rem !important;
    margin: 0 !important;
    padding: .65rem 0 .85rem !important;
    border-bottom: 1px solid rgba(226, 217, 204, .86) !important;
    background: transparent !important;
}

.studio-brand-link,
.studio-brand-link:visited,
.studio-brand-link:hover,
.studio-brand-link:active {
    display: inline-flex;
    align-items: center;
    gap: .72rem;
    width: max-content;
    max-width: 100%;
    min-height: 2.85rem;
    text-decoration: none !important;
    color: var(--ink) !important;
}

.studio-brand-logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    width: 2.85rem;
    height: 2.85rem;
    border-radius: 999px;
    background: rgba(250, 247, 241, .94);
    box-shadow: inset 0 0 0 1px rgba(226, 217, 204, .58);
    overflow: hidden;
}

.studio-brand-logo img {
    display: block;
    width: 2.2rem;
    height: auto;
    object-fit: contain;
}

.studio-brand-copy {
    display: grid;
    gap: .14rem;
    min-width: 0;
}

.studio-brand-copy strong {
    color: var(--ink) !important;
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(1.08rem, 1.5vw, 1.42rem);
    font-weight: 500;
    letter-spacing: .015em;
    line-height: 1.05;
}

.studio-brand-copy span {
    color: var(--muted) !important;
    font-size: .74rem;
    font-weight: 740;
    letter-spacing: .08em;
    text-transform: uppercase;
}

"""

CSS = CSS
