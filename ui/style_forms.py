"""Shared Streamlit form and button styles."""

CSS = r"""
.stButton > button,
.stDownloadButton > button,
button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    min-height: 2.55rem !important;
    border-radius: var(--radius-control) !important;
    font-weight: 760 !important;
    letter-spacing: -0.004em !important;
    border: 1px solid rgba(199, 208, 202, 0.86) !important;
    box-shadow: var(--shadow-control) !important;
    transition: background .16s ease, border-color .16s ease, color .16s ease, transform .16s ease, box-shadow .16s ease !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(15, 106, 95, 0.70) !important;
    box-shadow: 0 6px 16px rgba(23, 34, 30, 0.07) !important;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(180deg, var(--teal) 0%, var(--teal-dark) 100%) !important;
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
    background: rgba(255, 253, 248, 0.92) !important;
    color: var(--ink) !important;
    border: 1px solid rgba(199, 208, 202, 0.92) !important;
}

.stButton > button:disabled,
.stDownloadButton > button:disabled,
button:disabled,
button[disabled] {
    background: #f0f2ef !important;
    color: #7a8881 !important;
    border-color: #dfe5e0 !important;
    opacity: 1 !important;
    box-shadow: none !important;
    transform: none !important;
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: rgba(255, 253, 248, 0.94) !important;
    color: var(--ink) !important;
    border: 1px solid rgba(199, 208, 202, 0.88) !important;
    border-radius: var(--radius-control) !important;
    box-shadow: var(--shadow-control) !important;
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
    min-height: 300px !important;
}

div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px rgba(15, 106, 95, 0.14) !important;
}

div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stTextInput"] input::placeholder {
    color: #71817b !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: rgba(255, 253, 248, 0.92) !important;
    border: 1px dashed rgba(199, 208, 202, 0.92) !important;
    border-radius: 18px !important;
    color: var(--ink-soft) !important;
}

[data-testid="stFileUploaderDropzone"] * {
    color: var(--ink-soft) !important;
}
"""
