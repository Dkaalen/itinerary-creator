"""Shared Streamlit form and button styles."""

CSS = r"""
.stButton > button,
.stDownloadButton > button,
button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    min-height: 2.45rem !important;
    border-radius: var(--radius-control) !important;
    font-weight: 760 !important;
    letter-spacing: 0.002em !important;
    border: 1px solid var(--line-strong) !important;
    box-shadow: none !important;
    transition: background .16s ease, border-color .16s ease, color .16s ease, transform .16s ease !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-1px) !important;
    border-color: var(--teal) !important;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: var(--teal-dark) !important;
    color: #ffffff !important;
    border-color: var(--teal-dark) !important;
}

.stButton > button[kind="primary"] *,
.stDownloadButton > button[kind="primary"] *,
[data-testid="stBaseButton-primary"] * {
    color: #ffffff !important;
}

.stButton > button:not([kind="primary"]),
.stDownloadButton > button:not([kind="primary"]) {
    background: rgba(255, 253, 250, 0.96) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line-strong) !important;
}

/* Red is reserved for high-intent actions such as exports and destructive buttons. */
.stDownloadButton > button {
    border-color: rgba(217, 75, 95, 0.38) !important;
}

.stButton > button:disabled,
.stDownloadButton > button:disabled,
button:disabled,
button[disabled] {
    background: #eef2f1 !important;
    color: #71808f !important;
    border-color: var(--line) !important;
    opacity: 1 !important;
    box-shadow: none !important;
    transform: none !important;
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: var(--paper) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: var(--radius-control) !important;
    box-shadow: none !important;
    outline: none !important;
}

div[data-baseweb="base-input"],
[data-baseweb="input"],
[data-baseweb="textarea"],
[data-baseweb="select"] {
    background: transparent !important;
    box-shadow: none !important;
    outline: none !important;
}

div[data-testid="stTextArea"] textarea {
    font-size: .98rem !important;
    line-height: 1.55 !important;
    padding: 1rem !important;
    min-height: 300px !important;
}

div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px rgba(13, 111, 104, 0.13) !important;
}

div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stTextInput"] input::placeholder {
    color: #6f7f8e !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: rgba(255, 253, 250, 0.95) !important;
    border: 1px dashed var(--line-strong) !important;
    border-radius: 14px !important;
    color: var(--ink-soft) !important;
}

[data-testid="stFileUploaderDropzone"] * {
    color: var(--ink-soft) !important;
}
"""
