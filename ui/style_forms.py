"""Shared Streamlit form and button styles."""

CSS = r"""
.stButton > button,
.stDownloadButton > button,
button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    min-height: 2.55rem !important;
    border-radius: var(--radius-control) !important;
    font-weight: 780 !important;
    letter-spacing: -0.006em !important;
    border: 1px solid rgba(207, 198, 183, 0.88) !important;
    box-shadow: var(--shadow-control) !important;
    transition: background .16s ease, border-color .16s ease, color .16s ease, transform .16s ease, box-shadow .16s ease !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(95, 87, 77, 0.62) !important;
    box-shadow: 0 8px 18px rgba(36, 37, 34, 0.075) !important;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(180deg, var(--sumi-2) 0%, var(--action) 100%) !important;
    color: #fffdf8 !important;
    border-color: rgba(47, 48, 45, 0.92) !important;
}

.stButton > button[kind="primary"] *,
.stDownloadButton > button[kind="primary"] *,
[data-testid="stBaseButton-primary"] * {
    color: #fffdf8 !important;
}

.stButton > button:not([kind="primary"]),
.stDownloadButton > button:not([kind="primary"]) {
    background: rgba(255, 253, 248, 0.92) !important;
    color: var(--ink) !important;
    border: 1px solid rgba(207, 198, 183, 0.92) !important;
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
    background: rgba(255, 253, 248, 0.96) !important;
    color: var(--ink) !important;
    border: 1px solid rgba(207, 198, 183, 0.90) !important;
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
    min-height: 330px !important;
}

div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: var(--accent-dark) !important;
    box-shadow: 0 0 0 3px rgba(129, 119, 105, 0.16) !important;
}

div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stTextInput"] input::placeholder {
    color: #7d7c74 !important;
    opacity: 1 !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: rgba(255, 253, 248, 0.92) !important;
    border: 1px dashed rgba(207, 198, 183, 0.92) !important;
    border-radius: 18px !important;
    color: var(--ink-soft) !important;
}

[data-testid="stFileUploaderDropzone"] * {
    color: var(--ink-soft) !important;
}
"""
