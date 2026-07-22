"""Compact project-manager, file-row, and backup-uploader styles."""

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

PROJECT_BROWSER_CSS = r""".open-project-workspace {
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
.open-project-workspace [data-testid="stCaptionContainer"],
.open-project-workspace [data-testid="stCaptionContainer"] * {
    color: #d9d4c9 !important;
}

.cloud-project-row,
.cloud-project-detail-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .65rem;
    border: 1px solid rgba(224, 216, 202, .86);
    border-radius: 12px;
    background: #fffdf8;
    padding: .62rem .72rem;
    margin: .28rem 0 .36rem;
}

.cloud-project-row.selected,
.cloud-project-detail-card {
    border-color: rgba(102, 126, 96, .58);
    box-shadow: inset 3px 0 0 rgba(76, 112, 79, .72);
}

.cloud-project-row.active,
.cloud-project-detail-card.active {
    background: #f3f7ef;
}

.cloud-project-row div,
.cloud-project-detail-card {
    min-width: 0;
}

.cloud-project-row strong,
.cloud-project-detail-card strong {
    display: block;
    overflow: hidden;
    color: #1f2630 !important;
    font-size: .9rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.cloud-project-row span,
.cloud-project-detail-card span,
.cloud-project-detail-card small {
    display: block;
    color: #66645f !important;
    font-size: .74rem;
    margin-top: .1rem;
}

.cloud-project-row small {
    color: #4c704f !important;
    font-size: .7rem;
    font-weight: 760;
    white-space: nowrap;
}

.cloud-project-detail-card {
    display: grid;
    gap: .15rem;
    padding: .85rem .9rem;
    margin-bottom: .65rem;
}

.cloud-file-row {
    display: grid;
    gap: .12rem;
    padding: .48rem 0 .28rem;
}

.cloud-file-row strong {
    color: #1f2630 !important;
    font-size: .86rem;
    font-weight: 760;
}

.cloud-file-row span {
    color: #66645f !important;
    font-size: .74rem;
}

.cloud-project-delete-warning {
    display: grid;
    gap: .22rem;
    margin: .6rem 0 .55rem;
    padding: .72rem .85rem;
    border: 1px solid rgba(178, 76, 67, .35);
    border-radius: 12px;
    background: rgba(178, 76, 67, .10);
}

.cloud-project-delete-warning strong {
    color: #792f29 !important;
}

.cloud-project-delete-warning span {
    color: #704944 !important;
    font-size: .82rem;
}

.block-container:has(.open-project-workspace) div[data-testid="stFileUploader"],
.block-container:has(.open-project-workspace) [data-testid="stAlert"] {
    margin-left: clamp(1.15rem, 2.4vw, 2rem) !important;
    margin-right: clamp(1.15rem, 2.4vw, 2rem) !important;
}

.st-key-cloud_project_manager {
    background: rgba(255, 253, 248, .96) !important;
}

.block-container:has(.open-project-workspace) div[data-testid="stTextInput"] input,
.block-container:has(.open-project-workspace) div[data-testid="stSelectbox"] > div > div,
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
    color: #1f2630 !important;
}

.block-container:has(.open-project-workspace) [data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 253, 248, .96) !important;
    border-color: rgba(224, 216, 202, .9) !important;
    border-radius: 16px !important;
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

@media (max-width: 760px) {
    .cloud-project-row,
    .cloud-project-detail-card {
        padding: .58rem .64rem;
    }
}
"""

CSS = "\n".join((PROJECT_COPY_CSS, PROJECT_BROWSER_CSS))
