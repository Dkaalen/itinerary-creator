"""Input, calculator, local-library, and supplier-preview workspace styles."""

PAGE_LAYOUT_CSS = r"""
.input-page-heading,
.workspace-page-heading {
    margin: .15rem 0 1rem;
    max-width: 760px;
}
.input-page-heading h1,
.workspace-page-heading h1 {
    margin: 0;
    color: var(--ink) !important;
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(2.35rem, 4vw, 3.8rem);
    font-weight: 500;
    line-height: 1;
    letter-spacing: -.045em;
}
.workspace-page-heading h1 { font-size: clamp(2rem, 3vw, 3rem); }
.input-page-heading p {
    margin: .6rem 0 0;
    color: var(--ink-soft) !important;
    font-size: .96rem;
    line-height: 1.45;
}
.input-page-kicker,
.calculator-kicker,
.source-line span {
    color: #6e665c !important;
    font-size: .69rem;
    font-weight: 800;
    letter-spacing: .13em;
    text-transform: uppercase;
}

.st-key-input_workspace_form {
    max-width: 1180px;
    margin: 0 auto;
    padding: 1rem 0 0;
}
.source-line {
    display: flex;
    align-items: center;
    margin: .85rem 0 .42rem;
}
.block-container:has(.input-page-heading) div[data-testid="stTextInput"],
.block-container:has(.input-page-heading) div[data-testid="stTextArea"],
.block-container:has(.input-page-heading) [data-testid="stWidgetLabel"] {
    margin-left: 0 !important;
    margin-right: 0 !important;
    width: 100% !important;
}
.block-container:has(.input-page-heading) div[data-testid="stTextInput"] {
    margin-top: 0 !important;
    margin-bottom: .65rem !important;
}
.block-container:has(.input-page-heading) div[data-testid="stTextArea"] textarea {
    min-height: 280px !important;
    max-height: 46vh !important;
}
.block-container:has(.input-page-heading) [data-testid="stWidgetLabel"] {
    margin-bottom: .35rem !important;
}
.block-container:has(.input-page-heading) [data-testid="stWidgetLabel"] p {
    color: #6e665c !important;
    font-size: .69rem !important;
    font-weight: 800 !important;
    letter-spacing: .13em !important;
    text-transform: uppercase !important;
}
.st-key-input_generation_actions {
    margin: .8rem 0 0 !important;
}
.st-key-input_generation_actions button { min-height: 2.8rem !important; }

.local-library-heading { padding-bottom: .2rem; }
.block-container:has(.local-library-heading) .workspace-page-heading,
.block-container:has(.local-library-heading) div[data-testid="stTextInput"],
.block-container:has(.local-library-heading) div[data-testid="stAlert"],
.block-container:has(.local-library-heading) div[data-testid="stSelectbox"] {
    margin-left: 0 !important;
    margin-right: 0 !important;
    width: 100% !important;
}
.block-container:has(.local-library-heading) [data-testid="stExpander"],
.block-container:has(.local-library-heading) [data-testid="stForm"] {
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding: .1rem .25rem !important;
    background: #fff !important;
    border-color: var(--line) !important;
}
.block-container:has(.local-library-heading) [data-testid="stAlert"] *,
.block-container:has(.local-library-heading) [data-testid="stExpander"] * { color: var(--ink) !important; }

@media (max-width: 620px) {
    .input-page-heading, .workspace-page-heading { margin-left: 0; margin-right: 0; }
    .block-container:has(.input-page-heading) div[data-testid="stTextArea"] textarea { min-height: 240px !important; }
}
"""

SUPPLIER_PREVIEW_CSS = r""".supplier-preview-panel {
    margin: .75rem 0 0;
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
