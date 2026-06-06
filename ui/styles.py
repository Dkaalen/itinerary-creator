"""Shared Streamlit styling for the internal itinerary app."""

import streamlit as st


def apply_global_styles():
    st.markdown(
        """
        <style>
            :root {
                --app-bg: #f5f1ea;
                --paper: #fffdf8;
                --surface: #ffffff;
                --surface-soft: #f8fafc;
                --ink: #132033;
                --ink-soft: #344054;
                --muted: #5b6678;
                --line: #d8e0ea;
                --line-strong: #b9c7d6;
                --navy: #081527;
                --navy-2: #102d46;
                --teal: #007f79;
                --teal-dark: #005f5b;
                --gold: #a86f16;
                --warning: #b45309;
                --danger: #b42318;
                --success: #087443;
                --shadow-soft: 0 22px 55px rgba(16, 32, 51, 0.12);
                --shadow-card: 0 12px 30px rgba(16, 32, 51, 0.09);
            }

            html, body, [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at top left, rgba(0, 127, 121, 0.10), transparent 34rem),
                    linear-gradient(180deg, #fffdf8 0%, var(--app-bg) 100%) !important;
                color: var(--ink) !important;
            }

            .block-container {
                max-width: 1380px;
                padding-top: 1.4rem;
                padding-bottom: 5rem;
            }

            h1, h2, h3, h4, h5, h6 {
                color: var(--ink) !important;
                letter-spacing: -0.035em;
            }

            p, li, label, [data-testid="stMarkdownContainer"] {
                color: var(--ink-soft) !important;
            }

            label, [data-testid="stWidgetLabel"] p {
                color: var(--ink) !important;
                font-weight: 750 !important;
            }

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


            .luxury-hero {
                position: relative;
                display: grid;
                grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.75fr);
                gap: 1.3rem;
                align-items: stretch;
                padding: clamp(1.4rem, 3vw, 2.25rem);
                border-radius: 32px;
                background:
                    radial-gradient(circle at 85% 15%, rgba(168, 111, 22, 0.34), transparent 16rem),
                    radial-gradient(circle at 16% 35%, rgba(0, 127, 121, 0.28), transparent 17rem),
                    linear-gradient(135deg, #081527 0%, #143652 66%, #0b7b78 135%);
                border: 1px solid rgba(255,255,255,0.18);
                box-shadow: var(--shadow-soft);
                overflow: hidden;
            }

            .luxury-hero::after {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(90deg, rgba(255,255,255,.10), transparent 46%);
                pointer-events: none;
            }

            .luxury-hero-main,
            .hero-summary-card {
                position: relative;
                z-index: 1;
            }

            .hero-eyebrow,
            .section-kicker {
                color: #d7b56d !important;
                font-size: 0.78rem;
                font-weight: 900;
                letter-spacing: .16em;
                text-transform: uppercase;
                margin-bottom: .55rem;
            }

            .luxury-hero h1 {
                color: #ffffff !important;
                font-size: clamp(2.3rem, 5vw, 4.65rem);
                line-height: .95;
                margin: 0;
                max-width: 880px;
            }

            .luxury-hero p {
                color: #e6eff7 !important;
                max-width: 760px;
                margin: 1rem 0 0;
                font-size: 1.06rem;
                line-height: 1.55;
            }

            .hero-summary-card {
                align-self: end;
                background: rgba(255,255,255,0.14);
                border: 1px solid rgba(255,255,255,0.24);
                border-radius: 24px;
                padding: 1rem 1.1rem;
                backdrop-filter: blur(14px);
            }

            .hero-summary-card div {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                padding: .58rem 0;
                border-bottom: 1px solid rgba(255,255,255,0.13);
            }

            .hero-summary-card div:last-child { border-bottom: 0; }
            .hero-summary-card span {
                color: #cbd8e6 !important;
                font-size: .78rem;
                text-transform: uppercase;
                letter-spacing: .10em;
                font-weight: 850;
            }
            .hero-summary-card strong {
                color: #ffffff !important;
                text-align: right;
                font-weight: 900;
            }

            .app-version-pill {
                display: inline-flex;
                margin: .8rem 0 1.1rem;
                padding: .35rem .7rem;
                border: 1px solid var(--line);
                border-radius: 999px;
                background: rgba(255,255,255,.78);
                color: var(--muted) !important;
                font-size: .78rem;
                font-weight: 750;
            }

            .flow-nav {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: .75rem;
                margin: 0 0 1.4rem;
            }

            .flow-nav-item {
                display: flex;
                align-items: center;
                gap: .7rem;
                padding: .9rem 1rem;
                border-radius: 20px;
                border: 1px solid var(--line);
                background: #ffffff;
                box-shadow: 0 8px 20px rgba(16,32,51,.05);
            }

            .flow-nav-item span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 2rem;
                height: 2rem;
                border-radius: 999px;
                font-weight: 900;
                background: #e7f4f2;
                color: var(--teal-dark) !important;
            }

            .flow-nav-item strong {
                color: var(--ink) !important;
                font-size: .96rem;
            }

            .flow-nav-current {
                border-color: rgba(0,127,121,.46);
                box-shadow: 0 12px 26px rgba(0,127,121,.12);
            }

            .flow-nav-current span {
                background: var(--teal-dark);
                color: #ffffff !important;
            }

            .flow-nav-done span {
                background: #dff7ed;
                color: #087443 !important;
            }

            .flow-nav-locked {
                background: #f8fafc;
            }

            .document-stage-panel,
            .bottom-cta {
                background: rgba(255,255,255,.92);
                border: 1px solid var(--line);
                border-radius: 26px;
                padding: 1.2rem 1.25rem;
                box-shadow: var(--shadow-card);
                margin-bottom: 1rem;
            }

            .document-stage-panel h2 {
                margin: 0;
                font-size: clamp(1.45rem, 2.4vw, 2.15rem);
            }

            .document-stage-panel p {
                margin: .55rem 0 0;
                color: var(--ink-soft) !important;
                max-width: 820px;
            }

            .bottom-cta {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 1.25rem;
                background: #fffdf8;
                border-color: rgba(0,127,121,.22);
            }

            .bottom-cta strong {
                display: block;
                color: var(--ink) !important;
                font-size: 1.05rem;
            }

            .bottom-cta span {
                display: block;
                color: var(--ink-soft) !important;
                margin-top: .2rem;
            }

            .metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: .8rem;
                margin: 1rem 0;
            }

            .metric-card,
            .workflow-step-card,
            .quality-callout {
                background: #ffffff;
                color: var(--ink) !important;
                border: 1px solid var(--line);
                border-radius: 22px;
                padding: 1rem;
                box-shadow: var(--shadow-card);
            }

            .metric-card-label,
            .workflow-step-eyebrow {
                color: var(--teal-dark) !important;
                font-weight: 900;
                text-transform: uppercase;
                letter-spacing: .10em;
                font-size: .74rem;
            }
            .metric-card-value,
            .workflow-step-title {
                color: var(--ink) !important;
                font-weight: 900;
                font-size: 1.2rem;
            }
            .metric-card-helper,
            .workflow-step-helper,
            .workflow-step-description,
            .workflow-note,
            .project-action-note {
                color: var(--ink-soft) !important;
            }

            .panel-card-title { color: var(--ink) !important; font-weight: 900; }

            [data-testid="stExpander"] {
                border-radius: 22px !important;
                border: 1px solid var(--line) !important;
                background: #ffffff !important;
                box-shadow: var(--shadow-card) !important;
            }

            iframe[title="visual_page_editor"] {
                border-radius: 28px !important;
                border: 1px solid var(--line) !important;
                box-shadow: var(--shadow-soft) !important;
                background: #fffdf8 !important;
            }


            .pdf-ready-panel {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
                margin: 1rem 0 .55rem;
                padding: 1rem 1.1rem;
                border: 1px solid rgba(8, 116, 67, .28);
                border-radius: 24px;
                background: linear-gradient(135deg, #ffffff 0%, #eefaf4 100%);
                box-shadow: var(--shadow-card);
            }

            .pdf-ready-panel strong {
                display: block;
                color: var(--ink) !important;
                font-size: 1.05rem;
                font-weight: 950;
            }

            .pdf-ready-panel span {
                display: block;
                color: var(--ink-soft) !important;
                margin-top: .2rem;
            }

            .pdf-ready-panel .pdf-ready-location {
                flex: 0 0 auto;
                margin: 0;
                padding: .35rem .7rem;
                border-radius: 999px;
                background: #dff7ed;
                color: #075f37 !important;
                font-size: .78rem;
                font-weight: 900;
                text-transform: uppercase;
                letter-spacing: .08em;
            }

            div[data-testid="stDownloadButton"]:has([data-testid="stBaseButton-primary"]),
            div[data-testid="stDownloadButton"]:has(button[kind="primary"]) {
                position: sticky !important;
                bottom: 1rem !important;
                z-index: 999 !important;
                padding: .55rem !important;
                border: 1px solid rgba(0, 95, 91, .28) !important;
                border-radius: 999px !important;
                background: rgba(255, 253, 248, .96) !important;
                box-shadow: 0 20px 42px rgba(16, 32, 51, .20) !important;
                backdrop-filter: blur(10px);
            }


            .image-bank-repair-panel {
                margin: 18px 0 12px;
                padding: 18px 20px;
                border: 1px solid #b45309;
                border-radius: 18px;
                background: #fff7ed;
                color: #111827;
                box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
            }
            .image-bank-repair-panel strong {
                display: block;
                font-size: 1.05rem;
                color: #7c2d12 !important;
                margin-bottom: 6px;
            }
            .image-bank-repair-panel span {
                display: block;
                color: #374151 !important;
                line-height: 1.5;
            }

            @media (max-width: 980px) {
                .luxury-hero { grid-template-columns: 1fr; }
                .flow-nav { grid-template-columns: 1fr 1fr; }
                .metric-grid { grid-template-columns: 1fr 1fr; }
            }

            @media (max-width: 620px) {
                .flow-nav { grid-template-columns: 1fr; }
                .metric-grid { grid-template-columns: 1fr; }
                .block-container { padding-left: 1rem; padding-right: 1rem; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
