"""Shared Streamlit form and button styles."""

CSS = r"""
.stButton > button,
.stDownloadButton > button,
button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    min-height: 2.42rem !important;
    border-radius: var(--radius-control) !important;
    font-weight: 720 !important;
    letter-spacing: -0.006em !important;
    border: 1px solid var(--line-strong) !important;
    box-shadow: none !important;
    transition: background .16s ease, border-color .16s ease, color .16s ease, transform .16s ease !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(111, 102, 91, 0.58) !important;
    box-shadow: none !important;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: var(--action) !important;
    color: var(--action-text) !important;
    border-color: rgba(111, 102, 91, 0.46) !important;
}

.stButton > button[kind="primary"] *,
.stDownloadButton > button[kind="primary"] *,
[data-testid="stBaseButton-primary"] * {
    color: var(--action-text) !important;
}

.stButton > button:not([kind="primary"]),
.stDownloadButton > button:not([kind="primary"]) {
    background: rgba(255, 253, 248, 0.74) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line) !important;
}

.stButton > button:disabled,
.stDownloadButton > button:disabled,
button:disabled,
button[disabled] {
    background: #eeece6 !important;
    color: #85837a !important;
    border-color: #ded8cc !important;
    opacity: 1 !important;
    box-shadow: none !important;
    transform: none !important;
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: rgba(255, 253, 248, 0.84) !important;
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
    line-height: 1.58 !important;
    padding: 1.05rem !important;
    min-height: 420px !important;
}

div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: var(--accent-dark) !important;
    box-shadow: 0 0 0 3px rgba(154, 143, 127, 0.14) !important;
}

div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stTextInput"] input::placeholder {
    color: #85827a !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: rgba(255, 253, 248, 0.74) !important;
    border: 1px dashed var(--line-strong) !important;
    border-radius: 14px !important;
    color: var(--ink-soft) !important;
}

[data-testid="stFileUploaderDropzone"] * {
    color: var(--ink-soft) !important;
}
"""
