"""Calculator workspace layout and embedded spreadsheet styles."""

CALCULATOR_PAGE_CSS = r""".calculator-heading {
    padding-bottom: .35rem;
}

.block-container:has(.calculator-heading) {
    max-width: min(calc(100% - 3rem), 1540px) !important;
    width: min(calc(100% - 3rem), 1540px) !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}

.block-container:has(.calculator-heading) .workspace-page-heading,
.block-container:has(.calculator-heading) div[data-testid="stTextInput"],
.block-container:has(.calculator-heading) div[data-testid="stAlert"],
.block-container:has(.calculator-heading) div[data-testid="stSelectbox"] {
    margin-left: clamp(1.5rem, 3vw, 2.65rem) !important;
    margin-right: clamp(1.5rem, 3vw, 2.65rem) !important;
    width: auto !important;
}

.block-container:has(.calculator-heading) [data-testid="stExpander"],
.block-container:has(.calculator-heading) [data-testid="stForm"] {
    margin-left: clamp(1.5rem, 3vw, 2.65rem) !important;
    margin-right: clamp(1.5rem, 3vw, 2.65rem) !important;
    padding: .15rem .35rem !important;
    background: rgba(255, 253, 248, .68) !important;
    border-color: rgba(224, 216, 202, .76) !important;
}

.block-container:has(.calculator-heading) div[data-testid="element-container"]:has([data-testid="stCustomComponentV1"]),
.block-container:has(.calculator-heading) div[data-testid="element-container"]:has(iframe),
.block-container:has(.calculator-heading) div[data-testid="stCustomComponentV1"] {
    display: block !important;
    width: calc(100% - clamp(3rem, 6vw, 5.3rem)) !important;
    max-width: calc(100% - clamp(3rem, 6vw, 5.3rem)) !important;
    min-width: 0 !important;
    margin-left: clamp(1.5rem, 3vw, 2.65rem) !important;
    margin-right: clamp(1.5rem, 3vw, 2.65rem) !important;
}

.block-container:has(.calculator-heading) iframe,
.block-container:has(.calculator-heading) div[data-testid="stCustomComponentV1"] iframe {
    display: block !important;
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    border-radius: 18px !important;
    border: 1px solid rgba(207, 196, 179, .86) !important;
    box-shadow: none !important;
    background: #fffdf8 !important;
}

.block-container:has(.calculator-heading) [data-testid="stAlert"] *,
.block-container:has(.calculator-heading) [data-testid="stExpander"] * {
    color: var(--ink) !important;
}

.st-key-calculator_topbar {
    margin: .25rem clamp(1.5rem, 3vw, 2.65rem) 1.1rem;
    padding-bottom: .85rem;
    border-bottom: 1px solid rgba(207, 196, 179, .72);
}
.st-key-calculator_topbar button {
    min-height: 2.75rem;
    white-space: nowrap;
}

@media (max-width: 920px) {
    .st-key-calculator_topbar [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }
    .st-key-calculator_topbar [data-testid="column"] {
        flex: 1 1 min(100%, 13rem) !important;
        min-width: min(100%, 13rem) !important;
    }
}

@media (max-width: 740px) {
    .block-container:has(.calculator-heading) {
        max-width: min(calc(100% - 1rem), 1540px) !important;
        width: min(calc(100% - 1rem), 1540px) !important;
    }

    .block-container:has(.calculator-heading) div[data-testid="element-container"]:has([data-testid="stCustomComponentV1"]),
    .block-container:has(.calculator-heading) div[data-testid="element-container"]:has(iframe),
    .block-container:has(.calculator-heading) div[data-testid="stCustomComponentV1"] {
        width: calc(100% - 1rem) !important;
        max-width: calc(100% - 1rem) !important;
        min-width: 0 !important;
        margin-left: .5rem !important;
        margin-right: .5rem !important;
    }
}
"""

CSS = CALCULATOR_PAGE_CSS
