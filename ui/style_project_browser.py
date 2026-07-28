"""Project Explorer and backup-uploader styles."""

PROJECT_COPY_CSS = r"""
.project-explorer-heading {
    display: flex;
    align-items: center;
    gap: .7rem;
    margin: .25rem 0 .65rem;
    min-width: 0;
}
.project-explorer-heading > div { display: grid; gap: .08rem; min-width: 0; }
.project-explorer-folder {
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    flex: 0 0 auto;
    border-radius: 8px;
    background: #e1b95d;
    color: #3d2b08 !important;
    font-size: .95rem;
}
.project-explorer-heading strong { color: var(--ink) !important; font-size: 1rem; }
.project-explorer-heading span:not(.project-explorer-folder) {
    color: var(--ink-soft) !important;
    font-size: .8rem;
    line-height: 1.3;
}
"""

PROJECT_BROWSER_CSS = r"""
.st-key-cloud_project_explorer {
    margin-bottom: .75rem;
    padding: .8rem .85rem .7rem;
    background: #fff !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 24px rgba(31, 38, 48, .045);
}
.st-key-cloud_project_explorer [data-testid="stVerticalBlockBorderWrapper"] {
    background: transparent !important;
    border: 0 !important;
}
.st-key-cloud_project_explorer [data-testid="stForm"] {
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
}
.st-key-cloud_project_explorer label p {
    font-size: .7rem !important;
    font-weight: 760 !important;
    letter-spacing: .04em !important;
}
.st-key-cloud_project_explorer button { min-height: 2.55rem !important; white-space: nowrap; }
.st-key-cloud_project_explorer h4 { margin: .75rem 0 .35rem !important; font-size: 1.05rem !important; }
.st-key-cloud_project_explorer [data-testid="stDataFrame"] {
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 9px;
    background: #fff;
}
.st-key-cloud_project_explorer [data-testid="stDataFrame"] iframe { background: #fff; }

.cloud-project-empty-state,
.cloud-project-selection-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .75rem;
    margin: .55rem 0;
    padding: .65rem .75rem;
    border: 1px solid var(--line);
    border-radius: 9px;
    background: var(--surface-soft);
}
.cloud-project-empty-state {
    min-height: 5.5rem;
    display: grid;
    justify-content: stretch;
    align-content: center;
    text-align: center;
    gap: .15rem;
}
.cloud-project-empty-state strong,
.cloud-project-selection-summary strong { color: var(--ink) !important; font-size: .86rem; }
.cloud-project-empty-state span,
.cloud-project-selection-summary span { color: var(--ink-soft) !important; font-size: .76rem; }

.cloud-project-delete-warning {
    display: grid;
    gap: .18rem;
    margin: .55rem 0;
    padding: .7rem .78rem;
    border: 1px solid rgba(149, 77, 70, .42);
    border-radius: 9px;
    background: #fff5f3;
}
.cloud-project-delete-warning strong { color: #6f2f2a !important; }
.cloud-project-delete-warning span,
.cloud-project-delete-warning small { color: #704944 !important; font-size: .77rem; }

.cloud-file-row { display: grid; gap: .1rem; padding: .4rem 0 .2rem; }
.cloud-file-row strong { color: var(--ink) !important; font-size: .82rem; }
.cloud-file-row span { color: var(--ink-soft) !important; font-size: .72rem; }

.block-container:has(.project-explorer-heading) div[data-testid="stTextInput"] input,
.block-container:has(.project-explorer-heading) div[data-testid="stSelectbox"] > div > div,
.block-container:has(.project-explorer-heading) div[data-testid="stTextArea"] textarea {
    background: #fff !important;
    color: var(--ink) !important;
    border-color: var(--line-strong) !important;
}
.block-container:has(.project-explorer-heading) div[data-testid="stTextInput"] input::placeholder,
.block-container:has(.project-explorer-heading) div[data-testid="stTextArea"] textarea::placeholder {
    color: #716f69 !important;
    opacity: 1 !important;
}
.block-container:has(.project-explorer-heading) [data-testid="stFileUploaderDropzone"] {
    background: #fff !important;
    border-color: var(--line-strong) !important;
}
.block-container:has(.project-explorer-heading) [data-testid="stFileUploaderDropzone"] *,
.block-container:has(.project-explorer-heading) [data-testid="stFileUploader"] section * { color: var(--ink) !important; }

@media (max-width: 980px) {
    .st-key-cloud_project_explorer [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    .st-key-cloud_project_explorer [data-testid="column"] {
        min-width: min(100%, 15rem) !important;
        flex: 1 1 15rem !important;
    }
}
@media (max-width: 620px) {
    .project-explorer-heading span:not(.project-explorer-folder) { display: none; }
    .cloud-project-selection-summary { align-items: flex-start; flex-direction: column; }
    .st-key-cloud_project_explorer { padding: .55rem; }
}
"""

CSS = "\n".join((PROJECT_COPY_CSS, PROJECT_BROWSER_CSS))
