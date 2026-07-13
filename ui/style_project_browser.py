"""Open-project cloud browser, download rows, and modal contrast styles."""

PROJECT_COPY_CSS = r""".open-project-copy {
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

"""

PROJECT_BROWSER_CSS = r""".cloud-project-list {
    display: grid;
    gap: .65rem;
    margin: .65rem 0 1rem;
}

.cloud-project-card {
    border: 1px solid rgba(224, 216, 202, .78);
    border-radius: 14px;
    background: rgba(255, 253, 248, .72);
    padding: .75rem .85rem;
}

.cloud-project-card.active {
    border-color: rgba(102, 126, 96, .58);
    background: rgba(243, 247, 239, .88);
    box-shadow: inset 4px 0 0 rgba(76, 112, 79, .72);
}

.cloud-project-card strong {
    display: block;
    color: var(--ink) !important;
    font-size: .95rem;
}

.cloud-project-card span {
    display: block;
    color: var(--muted) !important;
    font-size: .78rem;
    margin-top: .16rem;
}


/* Open Project browser: inline workspace avoids Streamlit dialog fragments. */
.open-project-workspace {
    margin: .95rem 0 1rem;
    padding: 1rem 1.1rem;
    border: 1px solid rgba(224, 216, 202, .72);
    border-radius: 18px;
    background: #1f2630 !important;
    color: #f8f6f1 !important;
    box-shadow: 0 16px 36px rgba(0, 0, 0, .18);
}

.open-project-workspace .open-project-copy strong,
.open-project-workspace h1,
.open-project-workspace h2,
.open-project-workspace h3,
.open-project-workspace [data-testid="stMarkdownContainer"] strong {
    color: #fffdf8 !important;
}

.open-project-workspace .open-project-copy span,
.open-project-workspace p,
.open-project-workspace label,
.open-project-workspace [data-testid="stWidgetLabel"] p,
.open-project-workspace [data-testid="stMarkdownContainer"] p,
.open-project-workspace [data-testid="stCaptionContainer"],
.open-project-workspace [data-testid="stCaptionContainer"] * {
    color: #d9d4c9 !important;
}

.cloud-file-row {
    display: grid;
    gap: .12rem;
    padding: .55rem 0 .35rem;
}

.cloud-file-row strong {
    font-size: .88rem;
    font-weight: 760;
}

.cloud-file-row span {
    font-size: .76rem;
}

.cloud-project-delete-warning {
    display: grid;
    gap: .22rem;
    margin: .6rem 0 .55rem;
    padding: .72rem .85rem;
    border: 1px solid rgba(239, 120, 120, .34);
    border-radius: 12px;
    background: rgba(149, 77, 70, .18);
}

.cloud-project-delete-warning strong {
    color: #fffdf8 !important;
}

.cloud-project-delete-warning span {
    color: #e7d7d3 !important;
    font-size: .84rem;
}

/* The dark Open Project header is rendered with st.html, so target the active
   Streamlit block container rather than assuming later widgets are children. */
.block-container:has(.open-project-workspace) div[data-testid="stTextInput"],
.block-container:has(.open-project-workspace) div[data-testid="stFileUploader"],
.block-container:has(.open-project-workspace) [data-testid="stExpander"],
.block-container:has(.open-project-workspace) [data-testid="stAlert"],
.block-container:has(.open-project-workspace) [data-testid="stCaptionContainer"] {
    margin-left: clamp(1.15rem, 2.4vw, 2rem) !important;
    margin-right: clamp(1.15rem, 2.4vw, 2rem) !important;
}

.block-container:has(.open-project-workspace) div[data-testid="stTextInput"] input,
.block-container:has(.open-project-workspace) div[data-testid="stTextArea"] textarea {
    background: #fffdf8 !important;
    color: #1f2630 !important;
    border-color: rgba(224, 216, 202, .88) !important;
}

.block-container:has(.open-project-workspace) div[data-testid="stTextInput"] input::placeholder,
.block-container:has(.open-project-workspace) div[data-testid="stTextArea"] textarea::placeholder {
    color: #827c73 !important;
    opacity: 1 !important;
}

.block-container:has(.open-project-workspace) [data-testid="stWidgetLabel"] p,
.block-container:has(.open-project-workspace) label {
    color: #fffdf8 !important;
}

.block-container:has(.open-project-workspace) .cloud-project-list {
    gap: .85rem;
    margin: .9rem clamp(1.15rem, 2.4vw, 2rem) 1.1rem;
}

.block-container:has(.open-project-workspace) .cloud-project-card {
    background: #fffdf8 !important;
    border-color: rgba(224, 216, 202, .90) !important;
    padding: .95rem 1.05rem !important;
    box-shadow: 0 8px 22px rgba(0, 0, 0, .10) !important;
}

.block-container:has(.open-project-workspace) .cloud-project-card strong,
.block-container:has(.open-project-workspace) .cloud-file-row strong {
    color: #1f2630 !important;
}

.block-container:has(.open-project-workspace) .cloud-project-card span,
.block-container:has(.open-project-workspace) .cloud-file-row span {
    color: #5f625f !important;
}

.block-container:has(.open-project-workspace) [data-testid="stExpander"] {
    background: rgba(255, 253, 248, .10) !important;
    border-color: rgba(255, 253, 248, .22) !important;
}

.block-container:has(.open-project-workspace) [data-testid="stExpander"] summary,
.block-container:has(.open-project-workspace) [data-testid="stExpander"] summary * {
    color: #fffdf8 !important;
}

.block-container:has(.open-project-workspace) [data-testid="stFileUploaderDropzone"] {
    background: #fffdf8 !important;
    border-color: rgba(224, 216, 202, .88) !important;
}

.block-container:has(.open-project-workspace) [data-testid="stFileUploaderDropzone"] *,
.block-container:has(.open-project-workspace) [data-testid="stFileUploader"] section * {
    color: #1f2630 !important;
}

.calculator-download-ready-panel {
    margin: 1rem clamp(1.5rem, 3vw, 2.65rem) 0;
}

@media (max-width: 620px) {
    .input-page-heading,
    .workspace-page-heading,
    .source-line,
    .block-container:has(.input-page-heading) div[data-testid="stTextInput"],
    .block-container:has(.input-page-heading) div[data-testid="stTextArea"],
    .block-container:has(.input-page-heading) [data-testid="stWidgetLabel"],
    .block-container:has(.input-page-heading) div[data-testid="stHorizontalBlock"]:has(button[kind="primary"]),
    .block-container:has(.input-page-heading) div[data-testid="stHorizontalBlock"]:has([data-testid="stBaseButton-primary"]),
    .supplier-preview-panel {
        margin-left: 1.15rem !important;
        margin-right: 1.15rem !important;
    }
}
"""

CSS = "\n".join(
    (
    PROJECT_COPY_CSS,
    PROJECT_BROWSER_CSS,
    )
)
