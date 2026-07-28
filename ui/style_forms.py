"""Shared Streamlit form and button styles."""

CSS = r"""
.stButton button,
div[data-testid="stButton"] button,
.stDownloadButton button,
div[data-testid="stDownloadButton"] button,
button[kind="secondary"],
button[data-testid="baseButton-secondary"],
[data-testid="stBaseButton-secondary"],
button[kind="primary"],
button[data-testid="baseButton-primary"],
[data-testid="stBaseButton-primary"] {
    min-height: 2.8rem !important;
    border-radius: 10px !important;
    font-weight: 660 !important;
    letter-spacing: -0.006em !important;
    border: 1px solid var(--line-strong) !important;
    box-shadow: var(--shadow-control) !important;
    transition: background .16s ease, border-color .16s ease, color .16s ease, transform .16s ease, box-shadow .16s ease !important;
}

.stButton button:hover,
div[data-testid="stButton"] button:hover,
.stDownloadButton button:hover,
div[data-testid="stDownloadButton"] button:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(118, 107, 94, 0.58) !important;
    box-shadow: 0 8px 18px rgba(31, 38, 48, 0.07) !important;
}

.stButton button[kind="primary"],
div[data-testid="stButton"] button[kind="primary"],
.stDownloadButton button[kind="primary"],
div[data-testid="stDownloadButton"] button[kind="primary"],
button[data-testid="baseButton-primary"],
[data-testid="stBaseButton-primary"] {
    background: var(--primary-action) !important;
    color: var(--primary-action-text) !important;
    border-color: rgba(35, 52, 70, 0.78) !important;
}

.stButton button[kind="primary"] *,
div[data-testid="stButton"] button[kind="primary"] *,
.stDownloadButton button[kind="primary"] *,
div[data-testid="stDownloadButton"] button[kind="primary"] *,
button[data-testid="baseButton-primary"] *,
[data-testid="stBaseButton-primary"] * {
    color: var(--primary-action-text) !important;
}

.stButton button[kind="primary"]:hover,
div[data-testid="stButton"] button[kind="primary"]:hover,
.stDownloadButton button[kind="primary"]:hover,
div[data-testid="stDownloadButton"] button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: var(--primary-action-hover) !important;
}

.stButton button:not([kind="primary"]),
div[data-testid="stButton"] button:not([kind="primary"]),
.stDownloadButton button:not([kind="primary"]),
div[data-testid="stDownloadButton"] button:not([kind="primary"]),
button[data-testid="baseButton-secondary"],
[data-testid="stBaseButton-secondary"] {
    background: var(--action) !important;
    color: var(--action-text) !important;
    border-color: rgba(207, 196, 179, 0.86) !important;
}

.stButton button:not([kind="primary"]) *,
div[data-testid="stButton"] button:not([kind="primary"]) *,
.stDownloadButton button:not([kind="primary"]) *,
div[data-testid="stDownloadButton"] button:not([kind="primary"]) *,
button[data-testid="baseButton-secondary"] *,
[data-testid="stBaseButton-secondary"] * {
    color: var(--action-text) !important;
}

/* Header toolbar buttons: calm, light, spacious. */
div[data-testid="stHorizontalBlock"]:has(.studio-brand-link) div[data-testid="stButton"] button,
div[data-testid="stHorizontalBlock"]:has(.studio-brand-link) .stButton button {
    min-height: 3.35rem !important;
    border-radius: 10px !important;
    background: rgba(255, 253, 248, .72) !important;
    color: var(--ink) !important;
    border: 1px solid rgba(207, 196, 179, .78) !important;
    box-shadow: none !important;
    font-family: inherit !important;
    font-size: .9rem !important;
    font-weight: 650 !important;
}

div[data-testid="stHorizontalBlock"]:has(.studio-brand-link) div[data-testid="stButton"] button:hover,
div[data-testid="stHorizontalBlock"]:has(.studio-brand-link) .stButton button:hover {
    background: #ffffff !important;
    border-color: rgba(118, 107, 94, .45) !important;
    box-shadow: 0 8px 18px rgba(31, 38, 48, .055) !important;
}

.stButton button:disabled,
div[data-testid="stButton"] button:disabled,
.stDownloadButton button:disabled,
div[data-testid="stDownloadButton"] button:disabled,
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
    background: rgba(255, 253, 248, 0.72) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: var(--radius-control) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .72), var(--shadow-control) !important;
    outline: none !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    min-height: 3rem !important;
    padding-left: 1.1rem !important;
    padding-right: 1.1rem !important;
    font-family: inherit !important;
    font-size: .96rem !important;
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
    font-family: inherit !important;
    font-size: .96rem !important;
    line-height: 1.5 !important;
    padding: .9rem 1rem !important;
    min-height: 8rem !important;
}

div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {
    border-color: rgba(118, 107, 94, 0.72) !important;
    box-shadow: 0 0 0 3px rgba(168, 153, 134, 0.15), inset 0 1px 0 rgba(255,255,255,.72) !important;
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

/* Disabled controls must remain readable and must never retain a dark primary fill. */
div[data-testid="stButton"] button:disabled,
div[data-testid="stDownloadButton"] button:disabled,
button[data-testid="baseButton-primary"]:disabled,
button[data-testid="baseButton-secondary"]:disabled,
button[disabled] {
    background: #e7e4dd !important;
    color: #65625c !important;
    border-color: #d4cec2 !important;
    opacity: 1 !important;
}
div[data-testid="stButton"] button:disabled *,
div[data-testid="stDownloadButton"] button:disabled *,
button[data-testid="baseButton-primary"]:disabled *,
button[data-testid="baseButton-secondary"]:disabled *,
button[disabled] * {
    color: #65625c !important;
    opacity: 1 !important;
}

/* Destructive project actions are clearly separated from primary navigation. */
div[class*="st-key-delete_selected_cloud_project_"] button,
.st-key-bulk_delete_projects button,
.st-key-confirm_bulk_project_action button {
    background: #fff5f3 !important;
    color: #7b342e !important;
    border-color: rgba(149, 77, 70, .42) !important;
}
div[class*="st-key-delete_selected_cloud_project_"] button *,
.st-key-bulk_delete_projects button *,
.st-key-confirm_bulk_project_action button * {
    color: #7b342e !important;
}

button:focus-visible,
input:focus-visible,
textarea:focus-visible,
[data-baseweb="select"]:focus-within {
    outline: 3px solid rgba(64, 94, 121, .28) !important;
    outline-offset: 2px !important;
}
"""
