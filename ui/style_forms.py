"""Shared Streamlit form and button styles."""

CSS = r"""
.stButton > button,
            .stDownloadButton > button,
            button[kind="primary"],
            [data-testid="stBaseButton-primary"] {
                min-height: 2.65rem !important;
                border-radius: 12px !important;
                font-weight: 800 !important;
                letter-spacing: 0.005em !important;
                border: 1px solid var(--line-strong) !important;
                box-shadow: none !important;
            }

            .stButton > button[kind="primary"],
            .stDownloadButton > button[kind="primary"],
            [data-testid="stBaseButton-primary"] {
                background: var(--teal-dark) !important;
                color: #ffffff !important;
            }

            .stButton > button[kind="primary"] *,
            .stDownloadButton > button[kind="primary"] *,
            [data-testid="stBaseButton-primary"] * {
                color: #ffffff !important;
            }

            .stButton > button:not([kind="primary"]),
            .stDownloadButton > button:not([kind="primary"]) {
                background: #ffffff !important;
                color: var(--ink) !important;
                border: 1px solid var(--line-strong) !important;
                box-shadow: none !important;
            }

            .stButton > button:disabled,
            .stDownloadButton > button:disabled {
                background: #e4eaf1 !important;
                color: #5b6678 !important;
                opacity: 1 !important;
                box-shadow: none !important;
            }

            div[data-testid="stTextArea"] textarea,
            div[data-testid="stTextInput"] input,
            div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
                background: #ffffff !important;
                color: var(--ink) !important;
                border: 1px solid var(--line-strong) !important;
                border-radius: 12px !important;
                box-shadow: none !important;
            }

            div[data-testid="stTextArea"] textarea {
                font-size: 1rem !important;
                line-height: 1.55 !important;
                padding: 1rem !important;
            }

            div[data-testid="stTextArea"] textarea:focus,
            div[data-testid="stTextInput"] input:focus {
                border-color: var(--teal) !important;
                box-shadow: 0 0 0 3px rgba(14, 111, 107, 0.14) !important;
            }

            div[data-testid="stTextArea"] textarea::placeholder,
            div[data-testid="stTextInput"] input::placeholder {
                color: #667085 !important;
                opacity: 1 !important;
            }
"""
