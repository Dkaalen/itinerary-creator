"""Selected-project and bulk-action layout for Project Explorer."""

CSS = r"""
.cloud-project-selected-strip {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: .65rem 1rem;
    margin: .55rem 0 .45rem;
    padding: .72rem .78rem;
    border: 1px solid var(--line);
    border-radius: 9px;
    background: var(--surface-soft);
}
.cloud-project-selected-strip.active {
    border-color: rgba(76, 112, 79, .42);
    box-shadow: inset 3px 0 0 #5c7a5d;
}
.cloud-project-selected-title { display: grid; gap: .12rem; min-width: 0; }
.cloud-project-selected-title strong {
    overflow: hidden;
    color: var(--ink) !important;
    font-size: .9rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cloud-project-selected-title > span { color: var(--ink-soft) !important; font-size: .74rem; }
.cloud-project-selected-meta { display: flex; gap: 1rem; flex-wrap: wrap; justify-content: flex-end; }
.cloud-project-selected-meta span { color: var(--ink-soft) !important; font-size: .72rem; }
.cloud-project-selected-meta strong { color: var(--ink) !important; font-weight: 720; }
.cloud-project-active-badge {
    display: inline-block;
    width: fit-content;
    margin-left: .4rem;
    padding: .12rem .38rem;
    border-radius: 999px;
    background: #e9f2e6;
    color: #385b3d !important;
    font-size: .64rem;
    font-weight: 760;
}
div[class*="st-key-rename_cloud_project_form_"] [data-testid="stForm"] {
    max-width: 42rem;
}

@media (max-width: 760px) {
    .cloud-project-selected-strip { grid-template-columns: 1fr; }
    .cloud-project-selected-meta { justify-content: flex-start; }
}
"""
