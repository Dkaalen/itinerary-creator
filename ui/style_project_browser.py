"""Project Explorer, selected-detail, and backup-uploader styles."""

PROJECT_COPY_CSS = r""".project-explorer-heading {
    display: flex;
    align-items: center;
    gap: .8rem;
    margin: 1rem 0 .7rem;
    min-width: 0;
}

.project-explorer-heading > div {
    display: grid;
    gap: .16rem;
    min-width: 0;
}

.project-explorer-folder {
    display: grid;
    place-items: center;
    width: 2.35rem;
    height: 2.35rem;
    flex: 0 0 auto;
    border-radius: 9px;
    background: #d9b45f;
    color: #4f3a12 !important;
    font-size: 1.15rem;
}

.project-explorer-heading strong {
    color: var(--ink) !important;
    font-size: 1.1rem;
    letter-spacing: -.025em;
}

.project-explorer-heading span:not(.project-explorer-folder) {
    color: var(--ink-soft) !important;
    font-size: .88rem;
    line-height: 1.35;
}
"""

PROJECT_BROWSER_CSS = r""".st-key-cloud_project_explorer {
    margin-bottom: .8rem;
    background: #f7f8fa !important;
    border: 1px solid #d7dbe0 !important;
    border-radius: 12px !important;
    box-shadow: 0 10px 28px rgba(31, 38, 48, .08);
}

.st-key-cloud_project_explorer [data-testid="stVerticalBlockBorderWrapper"] {
    background: #f7f8fa !important;
    border-color: #d7dbe0 !important;
    border-radius: 12px !important;
}

.st-key-cloud_project_explorer [data-testid="stDataFrame"] {
    border: 1px solid #d7dbe0;
    border-radius: 8px;
    overflow: hidden;
    background: #ffffff;
}

.st-key-cloud_project_explorer [data-testid="stDataFrame"] iframe {
    background: #ffffff;
}

.cloud-project-detail-card {
    display: grid;
    gap: .7rem;
    min-width: 0;
    margin: 0 0 .65rem;
    padding: .9rem;
    border: 1px solid #d7dbe0;
    border-radius: 10px;
    background: #ffffff;
}

.cloud-project-detail-card.active {
    border-color: rgba(76, 112, 79, .55);
    box-shadow: inset 3px 0 0 rgba(76, 112, 79, .72);
    background: #f4f8f2;
}

.cloud-project-detail-card strong {
    overflow: hidden;
    color: #1f2630 !important;
    font-size: .98rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.cloud-project-detail-card dl {
    display: grid;
    gap: .42rem;
    margin: 0;
}

.cloud-project-detail-card dl > div {
    display: grid;
    grid-template-columns: 5rem minmax(0, 1fr);
    gap: .55rem;
}

.cloud-project-detail-card dt,
.cloud-project-detail-card dd {
    margin: 0;
    font-size: .76rem;
    line-height: 1.3;
}

.cloud-project-detail-card dt {
    color: #74777d !important;
}

.cloud-project-detail-card dd {
    overflow: hidden;
    color: #31363d !important;
    text-overflow: ellipsis;
    white-space: nowrap;
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
    border-radius: 10px;
    background: rgba(178, 76, 67, .10);
}

.cloud-project-delete-warning strong {
    color: #792f29 !important;
}

.cloud-project-delete-warning span {
    color: #704944 !important;
    font-size: .82rem;
}

.block-container:has(.project-explorer-heading) div[data-testid="stTextInput"] input,
.block-container:has(.project-explorer-heading) div[data-testid="stSelectbox"] > div > div,
.block-container:has(.project-explorer-heading) div[data-testid="stTextArea"] textarea {
    background: #ffffff !important;
    color: #1f2630 !important;
    border-color: #d7dbe0 !important;
}

.block-container:has(.project-explorer-heading) div[data-testid="stTextInput"] input::placeholder,
.block-container:has(.project-explorer-heading) div[data-testid="stTextArea"] textarea::placeholder {
    color: #7a7f86 !important;
    opacity: 1 !important;
}

.block-container:has(.project-explorer-heading) [data-testid="stFileUploaderDropzone"] {
    background: #ffffff !important;
    border-color: #d7dbe0 !important;
}

.block-container:has(.project-explorer-heading) [data-testid="stFileUploaderDropzone"] *,
.block-container:has(.project-explorer-heading) [data-testid="stFileUploader"] section * {
    color: #1f2630 !important;
}

.calculator-download-ready-panel {
    margin: 1rem clamp(1.5rem, 3vw, 2.65rem) 0;
}

@media (max-width: 900px) {
    .st-key-cloud_project_explorer [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    .st-key-cloud_project_explorer [data-testid="column"] {
        min-width: min(100%, 22rem) !important;
        flex: 1 1 22rem !important;
    }
}
"""

CSS = "\n".join((PROJECT_COPY_CSS, PROJECT_BROWSER_CSS))
