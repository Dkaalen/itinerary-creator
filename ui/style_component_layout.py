"""Shared responsive layout and text-fit rules for Streamlit workspaces."""

CSS = r"""
/* Keep all Streamlit layout children shrinkable instead of forcing overflow. */
div[data-testid="stHorizontalBlock"],
div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
div[data-testid="stVerticalBlock"],
div[data-testid="element-container"],
div[data-testid="stForm"] {
    min-width: 0 !important;
    max-width: 100% !important;
}

/* Button labels must remain inside their controls at every width. */
div[data-testid="stButton"] button,
div[data-testid="stDownloadButton"] button,
button[data-testid^="baseButton-"] {
    height: auto !important;
    padding: .68rem .9rem !important;
    white-space: normal !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

div[data-testid="stButton"] button p,
div[data-testid="stButton"] button span,
div[data-testid="stDownloadButton"] button p,
div[data-testid="stDownloadButton"] button span,
button[data-testid^="baseButton-"] p,
button[data-testid^="baseButton-"] span {
    min-width: 0 !important;
    max-width: 100% !important;
    margin: 0 !important;
    line-height: 1.22 !important;
    overflow-wrap: anywhere !important;
    word-break: normal !important;
    text-align: center !important;
}

/* Input values and alerts should never stretch their parent boxes. */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
div[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stAlert"],
[data-testid="stAlert"] > div,
[data-testid="stAlert"] p,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    min-width: 0 !important;
    max-width: 100% !important;
    overflow-wrap: anywhere !important;
}

div[data-testid="stSelectbox"] [data-baseweb="select"] span {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

/* Owned action rows. Wide screens keep hierarchy; narrow screens wrap cleanly. */
.st-key-workflow_stage_actions,
.st-key-input_top_actions,
.st-key-input_generation_actions,
.st-key-calculator_topbar,
.st-key-local_library_topbar,
.st-key-local_library_filters,
.st-key-local_library_paging,
.st-key-save_project_actions,
.st-key-save_as_project_actions,
.st-key-calculator_currency_editor,
.st-key-local_library_metrics,
div[class*="st-key-workflow_transaction_actions_"] {
    min-width: 0 !important;
    max-width: 100% !important;
}

.st-key-workflow_stage_actions {
    margin: .35rem 0 1rem;
    padding: .72rem;
    border: 1px solid rgba(224, 216, 202, .78);
    border-radius: 14px;
    background: rgba(255, 253, 248, .64);
}

.st-key-input_top_actions,
.st-key-input_generation_actions,
.st-key-calculator_topbar,
.st-key-local_library_topbar {
    margin-left: 0;
    margin-right: 0;
}

.st-key-input_generation_actions {
    margin-top: .8rem;
}

div[class*="st-key-workflow_transaction_actions_"] {
    margin-top: .55rem;
}

.st-key-local_library_metrics [data-testid="stMetric"] {
    min-width: 0 !important;
    padding: .72rem .8rem;
    border: 1px solid rgba(224, 216, 202, .72);
    border-radius: 12px;
    background: rgba(255, 253, 248, .58);
}

.st-key-local_library_metrics [data-testid="stMetricValue"],
.st-key-local_library_metrics [data-testid="stMetricLabel"] {
    min-width: 0 !important;
    overflow-wrap: anywhere !important;
}

@media (max-width: 980px) {
    .st-key-input_top_actions div[data-testid="stHorizontalBlock"],
    .st-key-calculator_topbar div[data-testid="stHorizontalBlock"],
    .st-key-local_library_topbar div[data-testid="stHorizontalBlock"],
    .st-key-local_library_filters div[data-testid="stHorizontalBlock"],
    .st-key-local_library_paging div[data-testid="stHorizontalBlock"],
    .st-key-calculator_currency_editor div[data-testid="stHorizontalBlock"],
    .st-key-local_library_metrics div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }

    .st-key-input_top_actions div[data-testid="column"],
    .st-key-calculator_topbar div[data-testid="column"],
    .st-key-local_library_topbar div[data-testid="column"] {
        flex: 1 1 12rem !important;
        width: auto !important;
    }

    .st-key-local_library_filters div[data-testid="column"],
    .st-key-local_library_paging div[data-testid="column"],
    .st-key-calculator_currency_editor div[data-testid="column"],
    .st-key-local_library_metrics div[data-testid="column"] {
        flex: 1 1 9rem !important;
        width: auto !important;
    }
}

@media (max-width: 760px) {
    .st-key-workflow_stage_actions div[data-testid="stHorizontalBlock"],
    .st-key-input_generation_actions div[data-testid="stHorizontalBlock"],
    .st-key-save_project_actions div[data-testid="stHorizontalBlock"],
    .st-key-save_as_project_actions div[data-testid="stHorizontalBlock"],
    div[class*="st-key-workflow_transaction_actions_"] div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }

    .st-key-workflow_stage_actions div[data-testid="column"],
    .st-key-input_generation_actions div[data-testid="column"],
    .st-key-save_project_actions div[data-testid="column"],
    .st-key-save_as_project_actions div[data-testid="column"],
    div[class*="st-key-workflow_transaction_actions_"] div[data-testid="column"] {
        flex: 1 1 15rem !important;
        width: auto !important;
    }

    .st-key-input_top_actions,
    .st-key-input_generation_actions,
    .st-key-calculator_topbar,
    .st-key-local_library_topbar {
        margin-left: 0;
        margin-right: 0;
    }
}

@media (max-width: 520px) {
    .st-key-workflow_stage_actions div[data-testid="column"],
    .st-key-input_top_actions div[data-testid="column"],
    .st-key-input_generation_actions div[data-testid="column"],
    .st-key-calculator_topbar div[data-testid="column"],
    .st-key-local_library_topbar div[data-testid="column"],
    .st-key-local_library_filters div[data-testid="column"],
    .st-key-local_library_paging div[data-testid="column"],
    .st-key-save_project_actions div[data-testid="column"],
    .st-key-save_as_project_actions div[data-testid="column"],
    .st-key-calculator_currency_editor div[data-testid="column"],
    .st-key-local_library_metrics div[data-testid="column"],
    div[class*="st-key-workflow_transaction_actions_"] div[data-testid="column"] {
        flex-basis: 100% !important;
        width: 100% !important;
    }
}
"""
