"""Calculator workspace layout and embedded spreadsheet styles."""

CALCULATOR_PAGE_CSS = r"""
.calculator-heading {
    margin: .15rem 0 .8rem !important;
    padding: 0 !important;
}
.calculator-heading p {
    margin: .45rem 0 0;
    color: var(--ink-soft) !important;
    font-size: .92rem;
}

.block-container:has(.calculator-heading) {
    max-width: min(calc(100% - 2rem), 1380px) !important;
    width: min(calc(100% - 2rem), 1380px) !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}

.st-key-calculator_topbar {
    margin: 0 0 1rem !important;
    padding: .65rem 0 .85rem !important;
    border-bottom: 1px solid var(--line) !important;
}
.st-key-calculator_topbar button {
    min-height: 2.65rem !important;
    white-space: nowrap;
}

.st-key-calculator_setup_bar {
    margin: 0 0 .35rem;
    padding: .75rem;
    border: 1px solid var(--line);
    border-radius: 11px;
    background: #fff;
}
.st-key-calculator_setup_bar [data-testid="stExpander"] {
    margin: 0 !important;
}
.st-key-calculator_setup_bar [data-testid="stWidgetLabel"] p {
    font-size: .75rem !important;
}
.st-key-calculator_library_status {
    margin: .15rem 0 .5rem;
    min-height: 1.25rem;
}
.st-key-calculator_library_status [data-testid="stCaptionContainer"] p {
    margin: 0 !important;
    font-size: .76rem !important;
    color: var(--muted) !important;
}

.block-container:has(.calculator-heading) .workspace-page-heading,
.block-container:has(.calculator-heading) div[data-testid="stTextInput"],
.block-container:has(.calculator-heading) div[data-testid="stAlert"],
.block-container:has(.calculator-heading) div[data-testid="stSelectbox"] {
    margin-left: 0 !important;
    margin-right: 0 !important;
    width: 100% !important;
}

.block-container:has(.calculator-heading) div[data-testid="element-container"]:has([data-testid="stCustomComponentV1"]),
.block-container:has(.calculator-heading) div[data-testid="element-container"]:has(iframe),
.block-container:has(.calculator-heading) div[data-testid="stCustomComponentV1"] {
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    margin: 0 !important;
}
.block-container:has(.calculator-heading) iframe,
.block-container:has(.calculator-heading) div[data-testid="stCustomComponentV1"] iframe {
    display: block !important;
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    border-radius: 11px !important;
    border: 1px solid var(--line) !important;
    box-shadow: none !important;
    background: #fff !important;
}
.block-container:has(.calculator-heading) [data-testid="stAlert"] *,
.block-container:has(.calculator-heading) [data-testid="stExpander"] * { color: var(--ink) !important; }

@media (max-width: 920px) {
    .st-key-calculator_topbar [data-testid="stHorizontalBlock"],
    .st-key-calculator_setup_bar [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    .st-key-calculator_topbar [data-testid="column"] { flex: 1 1 12rem !important; min-width: min(100%, 12rem) !important; }
    .st-key-calculator_setup_bar [data-testid="column"] { flex: 1 1 20rem !important; min-width: min(100%, 20rem) !important; }
}
@media (max-width: 740px) {
    .block-container:has(.calculator-heading) {
        max-width: calc(100% - 1rem) !important;
        width: calc(100% - 1rem) !important;
    }
    .st-key-calculator_setup_bar { padding: .55rem; }
}
"""

CSS = CALCULATOR_PAGE_CSS
