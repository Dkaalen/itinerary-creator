"""Shared Streamlit form and button styles."""

CSS = r"""
.stButton > button,
            .stDownloadButton > button,
            button[kind="primary"],
            [data-testid="stBaseButton-primary"] {
                min-height: 3.15rem !important;
                border-radius: 999px !important;
                font-weight: 850 !important;
                letter-spacing: 0.01em !important;
                border: 1px solid rgba(255,255,255,0.14) !important;
                box-shadow: 0 14px 28px rgba(0, 95, 91, 0.18) !important;
            }

            .stButton > button[kind="primary"],
            .stDownloadButton > button[kind="primary"],
            [data-testid="stBaseButton-primary"] {
                background: linear-gradient(135deg, var(--teal-dark), var(--teal)) !important;
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
                box-shadow: 0 8px 18px rgba(16, 32, 51, 0.06) !important;
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
                border: 1.5px solid var(--line-strong) !important;
                border-radius: 18px !important;
                box-shadow: 0 10px 24px rgba(16, 32, 51, 0.06) !important;
            }

            div[data-testid="stTextArea"] textarea {
                font-size: 1rem !important;
                line-height: 1.55 !important;
                padding: 1rem !important;
            }

            div[data-testid="stTextArea"] textarea:focus,
            div[data-testid="stTextInput"] input:focus {
                border-color: var(--teal) !important;
                box-shadow: 0 0 0 4px rgba(0, 127, 121, 0.16) !important;
            }

            div[data-testid="stTextArea"] textarea::placeholder,
            div[data-testid="stTextInput"] input::placeholder {
                color: #667085 !important;
                opacity: 1 !important;
            }
"""
