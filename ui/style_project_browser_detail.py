"""Selected-project and bulk-action layout for Project Explorer."""

CSS = r"""
.st-key-cloud_project_explorer .cloud-project-detail-card {
    grid-template-columns: minmax(15rem, 1.35fr) minmax(22rem, 2fr);
    align-items: center;
    gap: .75rem 1.25rem;
    margin-top: .35rem;
    padding: .8rem .9rem;
}
.st-key-cloud_project_explorer .cloud-project-detail-title,
.st-key-cloud_project_explorer .cloud-project-path {
    grid-column: 1;
}
.st-key-cloud_project_explorer .cloud-project-detail-card dl {
    grid-column: 2;
    grid-row: 1 / span 2;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .65rem;
}
.st-key-cloud_project_explorer .cloud-project-detail-card dl > div {
    display: grid;
    grid-template-columns: 1fr;
    gap: .12rem;
}
.st-key-cloud_project_explorer .cloud-project-manage-summary {
    margin-top: .45rem;
}
.st-key-cloud_project_explorer [data-testid="stForm"] {
    max-width: 46rem;
}
@media (max-width: 900px) {
    .st-key-cloud_project_explorer .cloud-project-detail-card {
        grid-template-columns: 1fr;
    }
    .st-key-cloud_project_explorer .cloud-project-detail-card dl {
        grid-column: 1;
        grid-row: auto;
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
@media (max-width: 620px) {
    .st-key-cloud_project_explorer .cloud-project-detail-card dl {
        grid-template-columns: 1fr;
    }
}

"""
