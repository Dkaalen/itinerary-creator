"""Project Explorer and backup-uploader styles."""

PROJECT_COPY_CSS = r"""
.st-key-project_explorer_workspace .project-explorer-heading {
    display: flex;
    align-items: center;
    gap: .7rem;
    margin: .25rem 0 .65rem;
    min-width: 0;
}
.st-key-project_explorer_workspace .project-explorer-heading > div {
    display: grid;
    gap: .08rem;
    min-width: 0;
}
.st-key-project_explorer_workspace .project-explorer-folder {
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
.st-key-project_explorer_workspace .project-explorer-heading strong {
    color: var(--ink) !important;
    font-size: 1rem;
}
.st-key-project_explorer_workspace .project-explorer-heading span:not(.project-explorer-folder) {
    color: var(--ink-soft) !important;
    font-size: .8rem;
    line-height: 1.3;
}
"""

PROJECT_BROWSER_CSS = r"""
.st-key-project_explorer_workspace {
    min-width: 0 !important;
    max-width: 100% !important;
    margin: .15rem 0 .9rem;
}
.st-key-project_explorer_header [data-testid="stHorizontalBlock"] {
    align-items: center;
}
.st-key-project_explorer_header button {
    min-height: 2.55rem !important;
}
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
.st-key-project_explorer_filter_form [data-testid="stForm"] {
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
}
.st-key-project_explorer_workspace label p {
    color: #5f625f !important;
    font-size: .7rem !important;
    font-weight: 760 !important;
    letter-spacing: .04em !important;
}
.st-key-project_explorer_workspace button {
    min-height: 2.55rem !important;
    white-space: nowrap;
}
.st-key-cloud_project_explorer h4 {
    margin: .75rem 0 .35rem !important;
    font-size: 1.05rem !important;
}
.st-key-cloud_project_explorer [data-testid="stCustomComponentV1"],
.st-key-cloud_project_explorer div[data-testid="element-container"]:has(iframe) {
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    margin: 0 !important;
}
.st-key-cloud_project_explorer [data-testid="stCustomComponentV1"] iframe,
.st-key-cloud_project_explorer div[data-testid="element-container"] > iframe {
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 100% !important;
    border: 0 !important;
    border-radius: 10px !important;
    background: #fff !important;
}

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

/* Project controls own only descendants of the keyed Project Explorer workspace. */
.st-key-project_explorer_workspace div[data-testid="stTextInput"] [data-baseweb="input"],
.st-key-project_explorer_workspace div[data-testid="stTextArea"] [data-baseweb="base-input"],
.st-key-project_explorer_workspace div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: #fff !important;
    color: var(--ink) !important;
}
.st-key-project_explorer_workspace div[data-testid="stTextInput"] input::placeholder,
.st-key-project_explorer_workspace div[data-testid="stTextArea"] textarea::placeholder {
    color: #716f69 !important;
    opacity: 1 !important;
}
.st-key-project_explorer_backup [data-testid="stFileUploaderDropzone"] {
    background: #fff !important;
}
.st-key-project_explorer_backup [data-testid="stFileUploaderDropzone"] *,
.st-key-project_explorer_backup [data-testid="stFileUploader"] section * {
    color: var(--ink) !important;
}
.st-key-project_explorer_filter_actions div[data-testid="stFormSubmitButton"] button[kind="primary"],
.st-key-project_explorer_bulk_actions div[data-testid="stButton"] button[kind="primary"] {
    background: var(--primary-action) !important;
    color: #fff !important;
}
.st-key-project_explorer_filter_actions div[data-testid="stFormSubmitButton"] button[kind="primary"] *,
.st-key-project_explorer_bulk_actions div[data-testid="stButton"] button[kind="primary"] * {
    color: #fff !important;
}

@media (max-width: 980px) {
    .st-key-project_explorer_filter_fields [data-testid="stHorizontalBlock"],
    .st-key-project_explorer_bulk_actions [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    .st-key-project_explorer_filter_fields [data-testid="column"] {
        flex: 1 1 12rem !important;
        width: auto !important;
        min-width: min(100%, 12rem) !important;
    }
    .st-key-project_explorer_bulk_actions [data-testid="column"] {
        flex: 1 1 14rem !important;
        width: auto !important;
        min-width: min(100%, 14rem) !important;
    }
}
@media (max-width: 760px) {
    .st-key-project_explorer_selected_actions [data-testid="stHorizontalBlock"],
    .st-key-project_explorer_open_confirmation [data-testid="stHorizontalBlock"],
    .st-key-project_explorer_delete_confirmation [data-testid="stHorizontalBlock"],
    .st-key-project_explorer_backup_confirmation [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    .st-key-project_explorer_selected_actions [data-testid="column"] {
        flex: 1 1 12rem !important;
        width: auto !important;
    }
    .st-key-project_explorer_open_confirmation [data-testid="column"],
    .st-key-project_explorer_delete_confirmation [data-testid="column"],
    .st-key-project_explorer_backup_confirmation [data-testid="column"] {
        flex: 1 1 14rem !important;
        width: auto !important;
    }
}
@media (max-width: 620px) {
    .st-key-project_explorer_workspace .project-explorer-heading span:not(.project-explorer-folder) { display: none; }
    .cloud-project-selection-summary { align-items: flex-start; flex-direction: column; }
    .st-key-cloud_project_explorer { padding: .55rem; }
    .st-key-project_explorer_header [data-testid="column"]:first-child { flex: 1 1 calc(100% - 6rem) !important; }
    .st-key-project_explorer_header [data-testid="column"]:last-child { flex: 0 0 5.5rem !important; }
    .st-key-project_explorer_filter_actions [data-testid="column"] { flex: 1 1 8rem !important; width: auto !important; }
    .st-key-project_explorer_filter_actions [data-testid="column"]:last-child { display: none !important; }
}
@media (max-width: 520px) {
    .st-key-project_explorer_filter_fields [data-testid="column"],
    .st-key-project_explorer_bulk_actions [data-testid="column"],
    .st-key-project_explorer_selected_actions [data-testid="column"],
    .st-key-project_explorer_open_confirmation [data-testid="column"],
    .st-key-project_explorer_delete_confirmation [data-testid="column"],
    .st-key-project_explorer_backup_confirmation [data-testid="column"] {
        flex-basis: 100% !important;
        width: 100% !important;
    }
}
"""

CSS = "\n".join((PROJECT_COPY_CSS, PROJECT_BROWSER_CSS))
