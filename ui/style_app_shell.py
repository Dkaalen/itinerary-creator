"""App shell, page chrome, and embedded editor frame styles."""

CSS = r"""
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
    max-width: min(100% - 3rem, 1480px) !important;
    width: min(100% - 3rem, 1480px) !important;
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
        max-width: min(100% - 1rem, 1480px) !important;
        width: min(100% - 1rem, 1480px) !important;
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
    margin-bottom: .78rem;
    position: relative;
}

.input-page-kicker::after {
    content: "";
    display: block;
    width: 2rem;
    height: 2px;
    margin-top: .72rem;
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
    margin: 0 0 clamp(3rem, 5.2vw, 4.25rem) !important;
    padding: 1.25rem clamp(1.5rem, 3.6vw, 2.65rem) !important;
    border-bottom: 1px solid rgba(226, 217, 204, .86) !important;
    background: rgba(255, 253, 248, .84) !important;
}

.studio-brand-link,
.studio-brand-link:visited,
.studio-brand-link:hover,
.studio-brand-link:active {
    display: inline-flex;
    align-items: center;
    gap: 1rem;
    width: max-content;
    max-width: 100%;
    min-height: 3.35rem;
    text-decoration: none !important;
    color: var(--ink) !important;
}

.studio-brand-logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    width: 3.35rem;
    height: 3.35rem;
    border-radius: 999px;
    background: rgba(250, 247, 241, .94);
    box-shadow: inset 0 0 0 1px rgba(226, 217, 204, .58);
    overflow: hidden;
}

.studio-brand-logo img {
    display: block;
    width: 2.65rem;
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
    font-size: clamp(1.18rem, 1.65vw, 1.58rem);
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

.input-page-heading,
.workspace-page-heading {
    margin: 0 clamp(2rem, 4.4vw, 3.6rem) 1.65rem;
    max-width: 820px;
}

.workspace-page-heading {
    margin-top: 0;
}

.input-page-heading h1,
.workspace-page-heading h1 {
    color: var(--ink) !important;
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(3.1rem, 5vw, 5rem);
    font-weight: 500;
    line-height: .96;
    letter-spacing: -.055em;
    margin: 0;
}

.workspace-page-heading h1 {
    font-size: clamp(2.35rem, 3.6vw, 3.6rem);
}

.input-page-heading p {
    color: var(--ink-soft) !important;
    font-size: 1rem;
    line-height: 1.55;
    margin: 1.45rem 0 0;
}

.source-line {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin: 2rem clamp(2rem, 4.4vw, 3.6rem) .66rem;
}

.block-container:has(.input-page-heading) div[data-testid="stTextInput"],
.block-container:has(.input-page-heading) div[data-testid="stTextArea"] {
    margin-left: clamp(2rem, 4.4vw, 3.6rem) !important;
    margin-right: clamp(2rem, 4.4vw, 3.6rem) !important;
    width: auto !important;
}

.block-container:has(.input-page-heading) div[data-testid="stTextInput"] {
    margin-top: .2rem !important;
    margin-bottom: 1.75rem !important;
}

.block-container:has(.input-page-heading) [data-testid="stWidgetLabel"] {
    margin-left: clamp(2rem, 4.4vw, 3.6rem) !important;
    margin-bottom: .56rem !important;
}

.block-container:has(.input-page-heading) [data-testid="stWidgetLabel"] p {
    color: var(--ink-soft) !important;
    font-size: .73rem !important;
    font-weight: 880 !important;
    letter-spacing: .18em !important;
    text-transform: uppercase !important;
}

.block-container:has(.input-page-heading) div[data-testid="stHorizontalBlock"]:has(button[kind="primary"]),
.block-container:has(.input-page-heading) div[data-testid="stHorizontalBlock"]:has([data-testid="stBaseButton-primary"]) {
    gap: 1.35rem !important;
    margin: 1.35rem clamp(2rem, 4.4vw, 3.6rem) 0 !important;
}

.calculator-heading,
.local-library-heading {
    padding-bottom: .35rem;
}

.block-container:has(.calculator-heading) .workspace-page-heading,
.block-container:has(.local-library-heading) .workspace-page-heading,
.block-container:has(.calculator-heading) div[data-testid="stTextInput"],
.block-container:has(.local-library-heading) div[data-testid="stTextInput"],
.block-container:has(.calculator-heading) div[data-testid="stAlert"],
.block-container:has(.local-library-heading) div[data-testid="stAlert"],
.block-container:has(.calculator-heading) div[data-testid="stSelectbox"],
.block-container:has(.local-library-heading) div[data-testid="stSelectbox"] {
    margin-left: clamp(1.5rem, 3vw, 2.65rem) !important;
    margin-right: clamp(1.5rem, 3vw, 2.65rem) !important;
    width: auto !important;
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

/* Do not let Streamlit border wrappers recreate the trapped outer app frame. */
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

@media (max-width: 620px) {
    .input-page-heading,
    .workspace-page-heading,
    .source-line,
    .block-container:has(.input-page-heading) div[data-testid="stTextInput"],
    .block-container:has(.input-page-heading) div[data-testid="stTextArea"],
    .block-container:has(.input-page-heading) [data-testid="stWidgetLabel"],
    .block-container:has(.input-page-heading) div[data-testid="stHorizontalBlock"]:has(button[kind="primary"]),
    .block-container:has(.input-page-heading) div[data-testid="stHorizontalBlock"]:has([data-testid="stBaseButton-primary"]) {
        margin-left: 1.15rem !important;
        margin-right: 1.15rem !important;
    }
}
"""
