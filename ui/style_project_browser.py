"""Project Explorer, selected-detail, and backup-uploader styles."""
PROJECT_COPY_CSS = r""".project-explorer-heading {
    display: flex;
    align-items: center;
    gap: .78rem;
    margin: .9rem 0 .65rem;
    min-width: 0;
}
.project-explorer-heading > div {
    display: grid;
    gap: .12rem;
    min-width: 0;
}
.project-explorer-folder {
    display: grid;
    place-items: center;
    width: 2.25rem;
    height: 2.25rem;
    flex: 0 0 auto;
    border-radius: 8px;
    background: #d9b45f;
    color: #4f3a12 !important;
    font-size: 1.08rem;
}
.project-explorer-heading strong {
    color: var(--ink) !important;
    font-size: 1.08rem;
    letter-spacing: -.025em;
}
.project-explorer-heading span:not(.project-explorer-folder) {
    color: var(--ink-soft) !important;
    font-size: .85rem;
    line-height: 1.32;
}
"""
PROJECT_BROWSER_CSS = r""".st-key-cloud_project_explorer {
    margin-bottom: .8rem;
    background: #f8f8f6 !important;
    border: 1px solid #d9d7d0 !important;
    border-radius: 12px !important;
    box-shadow: 0 5px 18px rgba(31, 38, 48, .055);
}
.st-key-cloud_project_explorer [data-testid="stVerticalBlockBorderWrapper"] {
    background: #f8f8f6 !important;
    border-color: #d9d7d0 !important;
    border-radius: 12px !important;
}
.st-key-cloud_project_explorer [data-testid="stForm"] {
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
}
.st-key-cloud_project_explorer label p {
    font-size: .75rem !important;
    font-weight: 720 !important;
    letter-spacing: .025em !important;
}
.st-key-cloud_project_explorer button {
    min-height: 2.65rem;
    white-space: nowrap;
}
.st-key-cloud_project_explorer [data-testid="stDataFrame"] {
    overflow: hidden;
    border: 1px solid #d5d4cf;
    border-radius: 9px;
    background: #ffffff;
}
.st-key-cloud_project_explorer [data-testid="stDataFrame"] iframe {
    background: #ffffff;
}
.cloud-project-detail-card {
    display: grid;
    gap: .62rem;
    min-width: 0;
    margin: 0 0 .62rem;
    padding: .88rem;
    border: 1px solid #d9d7d0;
    border-radius: 10px;
    background: #ffffff;
}
.cloud-project-detail-card.active {
    border-color: rgba(76, 112, 79, .5);
    box-shadow: inset 3px 0 0 rgba(76, 112, 79, .72);
    background: #f5f8f3;
}
.cloud-project-detail-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .55rem;
    min-width: 0;
}
.cloud-project-detail-card strong {
    color: #1f2630 !important;
}
.cloud-project-detail-title strong {
    overflow: hidden;
    min-width: 0;
    color: #1f2630 !important;
    font-size: .96rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cloud-project-active-badge {
    flex: 0 0 auto;
    padding: .18rem .43rem;
    border-radius: 999px;
    background: #e4eee1;
    color: #385b3d !important;
    font-size: .66rem;
    font-weight: 760;
}
.cloud-project-path {
    overflow: hidden;
    color: #686862 !important;
    font-size: .76rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cloud-project-detail-card dl {
    display: grid;
    gap: .38rem;
    margin: 0;
}
.cloud-project-detail-card dl > div {
    display: grid;
    grid-template-columns: 4.75rem minmax(0, 1fr);
    gap: .5rem;
}
.cloud-project-detail-card dt,
.cloud-project-detail-card dd {
    margin: 0;
    font-size: .74rem;
    line-height: 1.3;
}
.cloud-project-detail-card dt {
    color: #777771 !important;
}
.cloud-project-detail-card dd {
    overflow: hidden;
    color: #31363d !important;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cloud-project-manage-summary,
.cloud-project-empty-state {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .8rem;
    margin: .65rem 0;
    padding: .72rem .82rem;
    border: 1px solid #d9d7d0;
    border-radius: 9px;
    background: #ffffff;
}
.cloud-project-empty-state {
    display: grid;
    justify-content: stretch;
    gap: .2rem;
    min-height: 6rem;
    align-content: center;
    text-align: center;
}
.cloud-project-manage-summary strong,
.cloud-project-empty-state strong {
    color: #1f2630 !important;
    font-size: .9rem;
}
.cloud-project-manage-summary span,
.cloud-project-empty-state span {
    color: #6d6d67 !important;
    font-size: .78rem;
}
.cloud-file-row {
    display: grid;
    gap: .12rem;
    padding: .45rem 0 .24rem;
}
.cloud-file-row strong {
    color: #1f2630 !important;
    font-size: .84rem;
    font-weight: 760;
}
.cloud-file-row span {
    color: #66645f !important;
    font-size: .72rem;
}
.cloud-project-delete-warning {
    display: grid;
    gap: .2rem;
    margin: .6rem 0 .55rem;
    padding: .72rem .82rem;
    border: 1px solid rgba(178, 76, 67, .35);
    border-radius: 9px;
    background: rgba(178, 76, 67, .085);
}
.cloud-project-delete-warning strong {
    color: #792f29 !important;
}
.cloud-project-delete-warning span,
.cloud-project-delete-warning small {
    color: #704944 !important;
    font-size: .78rem;
}
.block-container:has(.project-explorer-heading) div[data-testid="stTextInput"] input,
.block-container:has(.project-explorer-heading) div[data-testid="stSelectbox"] > div > div,
.block-container:has(.project-explorer-heading) div[data-testid="stTextArea"] textarea {
    background: #fff !important;
    color: #1f2630 !important;
    border-color: #d5d4cf !important;
}
.block-container:has(.project-explorer-heading) div[data-testid="stTextInput"] input::placeholder,
.block-container:has(.project-explorer-heading) div[data-testid="stTextArea"] textarea::placeholder {
    color: #7a7f86 !important;
    opacity: 1 !important;
}
.block-container:has(.project-explorer-heading) [data-testid="stFileUploaderDropzone"] {
    background: #fff !important;
    border-color: #d5d4cf !important;
}
.block-container:has(.project-explorer-heading) [data-testid="stFileUploaderDropzone"] *,
.block-container:has(.project-explorer-heading) [data-testid="stFileUploader"] section * {
    color: #1f2630 !important;
}
.calculator-download-ready-panel {
    margin: 1rem clamp(1.5rem, 3vw, 2.65rem) 0;
}
@media (max-width: 980px) {
    .st-key-cloud_project_explorer [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }
    .st-key-cloud_project_explorer [data-testid="column"] {
        min-width: min(100%, 18rem) !important;
        flex: 1 1 18rem !important;
    }
}
@media (max-width: 620px) {
    .project-explorer-heading span:not(.project-explorer-folder) {
        display: none;
    }
    .cloud-project-manage-summary {
        align-items: flex-start;
        flex-direction: column;
    }
}
"""
CSS = "\n".join((PROJECT_COPY_CSS, PROJECT_BROWSER_CSS))
