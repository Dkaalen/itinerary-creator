"""Input, calculator, local-library, and supplier-preview workspace styles."""

PAGE_LAYOUT_CSS = r""".input-page-heading,
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

.block-container:has(.input-page-heading) div[data-testid="stTextArea"] textarea {
    min-height: 330px !important;
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

@media (max-width: 620px) {
    .source-line {
        align-items: flex-start;
        flex-direction: column;
        gap: .35rem;
        margin-left: .75rem;
        margin-right: .75rem;
    }

    .input-page-heading,
    .workspace-page-heading {
        margin-left: .75rem;
        margin-right: .75rem;
    }
}


.local-library-heading {
    padding-bottom: .35rem;
}

.block-container:has(.local-library-heading) .workspace-page-heading,
.block-container:has(.local-library-heading) div[data-testid="stTextInput"],
.block-container:has(.local-library-heading) div[data-testid="stAlert"],
.block-container:has(.local-library-heading) div[data-testid="stSelectbox"] {
    margin-left: clamp(1.5rem, 3vw, 2.65rem) !important;
    margin-right: clamp(1.5rem, 3vw, 2.65rem) !important;
    width: auto !important;
}

.block-container:has(.local-library-heading) [data-testid="stExpander"],
.block-container:has(.local-library-heading) [data-testid="stForm"] {
    margin-left: clamp(1.5rem, 3vw, 2.65rem) !important;
    margin-right: clamp(1.5rem, 3vw, 2.65rem) !important;
    padding: .15rem .35rem !important;
    background: rgba(255, 253, 248, .68) !important;
    border-color: rgba(224, 216, 202, .76) !important;
}

.block-container:has(.local-library-heading) [data-testid="stAlert"] *,
.block-container:has(.local-library-heading) [data-testid="stExpander"] * {
    color: var(--ink) !important;
}

"""

SUPPLIER_PREVIEW_CSS = r""".supplier-preview-panel {
    margin: .95rem clamp(2rem, 4.4vw, 3.6rem) 0;
    border: 1px solid rgba(224, 216, 202, .76);
    border-radius: 14px;
    background: rgba(255, 253, 248, .56);
    overflow: hidden;
}

.supplier-preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: .72rem .9rem;
    border-bottom: 1px solid rgba(224, 216, 202, .72);
}

.supplier-preview-header span {
    color: var(--muted) !important;
    font-size: .72rem;
    font-weight: 880;
    letter-spacing: .16em;
    text-transform: uppercase;
}

.supplier-preview-header strong {
    color: var(--ink-soft) !important;
    font-size: .82rem;
    font-weight: 760;
}

.supplier-preview-scroll {
    max-height: 260px;
    overflow: auto;
}

.supplier-preview-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    table-layout: fixed;
}

.supplier-preview-table th,
.supplier-preview-table td {
    border-bottom: 1px solid rgba(224, 216, 202, .62);
    border-right: 1px solid rgba(224, 216, 202, .45);
    padding: .58rem .72rem;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.supplier-preview-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: rgba(244, 239, 230, .96);
    color: var(--ink) !important;
    font-size: .72rem;
    font-weight: 820;
}

.supplier-preview-table td {
    color: var(--ink-soft) !important;
    font-size: .84rem;
    background: rgba(255, 253, 248, .72);
}

.supplier-preview-table th:nth-child(1),
.supplier-preview-table td:nth-child(1) { width: 7.5rem; }
.supplier-preview-table th:nth-child(2),
.supplier-preview-table td:nth-child(2) { width: 8.5rem; }
.supplier-preview-table th:nth-child(3),
.supplier-preview-table td:nth-child(3) { width: 8.5rem; }
.supplier-preview-table th:nth-child(4),
.supplier-preview-table td:nth-child(4) { width: 10rem; }

.supplier-preview-more {
    padding: .65rem .9rem;
    color: var(--muted) !important;
    font-size: .82rem;
    border-top: 1px solid rgba(224, 216, 202, .62);
}

"""

CSS = "\n".join(
    (
    PAGE_LAYOUT_CSS,
    SUPPLIER_PREVIEW_CSS,
    )
)
