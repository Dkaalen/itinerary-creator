"""Shared Streamlit styling for the internal itinerary app."""

import streamlit as st


def apply_global_styles():
    st.markdown(
        """
        <style>
            :root {
                --app-bg: #f3f6f8;
                --surface: #ffffff;
                --surface-soft: #f8fafc;
                --surface-glass: rgba(255, 255, 255, 0.78);
                --ink: #102033;
                --ink-soft: #475569;
                --muted: #64748b;
                --line: #dbe4ed;
                --line-strong: #c8d4e0;
                --navy: #071528;
                --navy-2: #0d2744;
                --teal: #0f9b8e;
                --teal-dark: #08756e;
                --gold: #c79a3b;
                --warning: #d97706;
                --danger: #b42318;
                --shadow-soft: 0 20px 45px rgba(15, 35, 55, 0.10);
                --shadow-card: 0 10px 30px rgba(15, 35, 55, 0.08);
            }

            html, body, [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at top left, rgba(15, 155, 142, 0.10), transparent 32rem),
                    linear-gradient(180deg, #f7fafc 0%, var(--app-bg) 100%) !important;
                color: var(--ink);
            }

            .block-container {
                padding-top: 1.25rem;
                padding-bottom: 4rem;
                max-width: 1540px;
            }

            h1, h2, h3, h4 {
                color: var(--ink);
                letter-spacing: -0.025em;
            }

            p, li, label, [data-testid="stMarkdownContainer"] {
                color: var(--ink-soft);
            }

            div[data-testid="stSidebar"] {
                background: linear-gradient(180deg, var(--navy) 0%, #06101f 100%);
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }

            div[data-testid="stSidebar"] * {
                color: rgba(255, 255, 255, 0.88) !important;
            }

            div[data-testid="stSidebar"] h2,
            div[data-testid="stSidebar"] h3 {
                margin-top: 0.35rem;
                color: #ffffff !important;
                letter-spacing: -0.02em;
            }

            div[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
            div[data-testid="stSidebar"] small,
            div[data-testid="stSidebar"] p {
                color: rgba(255, 255, 255, 0.68) !important;
            }

            div[data-testid="stSidebar"] [data-testid="stMetric"] {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 16px;
                padding: 0.65rem 0.75rem;
            }

            div[data-testid="stSidebar"] [data-testid="stSelectbox"] > div,
            div[data-testid="stSidebar"] [data-testid="stFileUploader"] section,
            div[data-testid="stSidebar"] [data-testid="stCheckbox"] {
                background: rgba(255, 255, 255, 0.04);
                border-radius: 14px;
            }

            .sidebar-brand {
                padding: 0.95rem 0.2rem 1.1rem 0.2rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.10);
                margin-bottom: 1rem;
            }

            .sidebar-brand-kicker {
                color: rgba(255, 255, 255, 0.58) !important;
                font-size: 0.72rem;
                font-weight: 750;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                margin-bottom: 0.35rem;
            }

            .sidebar-brand-title {
                color: #ffffff !important;
                font-size: 1.25rem;
                font-weight: 800;
                letter-spacing: -0.03em;
                line-height: 1.1;
            }

            .sidebar-brand-subtitle {
                color: rgba(255, 255, 255, 0.66) !important;
                font-size: 0.84rem;
                line-height: 1.45;
                margin-top: 0.5rem;
            }

            .app-shell-topbar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 1rem;
            }

            .app-shell-chip {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                border: 1px solid var(--line);
                border-radius: 999px;
                padding: 0.42rem 0.7rem;
                background: rgba(255, 255, 255, 0.72);
                color: var(--ink-soft);
                font-size: 0.82rem;
                font-weight: 650;
            }

            .app-hero {
                position: relative;
                overflow: hidden;
                border-radius: 28px;
                padding: 1.55rem 1.65rem;
                background:
                    radial-gradient(circle at 82% 18%, rgba(199, 154, 59, 0.28), transparent 15rem),
                    radial-gradient(circle at 15% 35%, rgba(15, 155, 142, 0.22), transparent 18rem),
                    linear-gradient(135deg, #071528 0%, #123a58 62%, #0f9b8e 145%);
                box-shadow: var(--shadow-soft);
                margin-bottom: 1.15rem;
                border: 1px solid rgba(255, 255, 255, 0.18);
            }

            .app-hero::after {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(90deg, rgba(255, 255, 255, 0.10), transparent 42%);
                pointer-events: none;
            }

            .app-hero-content {
                position: relative;
                z-index: 1;
                display: grid;
                grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.95fr);
                gap: 1.35rem;
                align-items: end;
            }

            .app-hero-kicker {
                color: rgba(255, 255, 255, 0.70) !important;
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0.16em;
                text-transform: uppercase;
                margin-bottom: 0.45rem;
            }

            .app-hero h1 {
                color: #ffffff;
                font-size: clamp(2rem, 4vw, 3.6rem);
                line-height: 0.98;
                margin: 0;
                max-width: 780px;
            }

            .app-hero p {
                color: rgba(255, 255, 255, 0.76) !important;
                margin: 0.72rem 0 0 0;
                font-size: 1rem;
                max-width: 720px;
            }

            .hero-stat-panel {
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 22px;
                padding: 1rem;
                background: rgba(255, 255, 255, 0.10);
                backdrop-filter: blur(14px);
            }

            .hero-stat-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 0.9rem;
                padding: 0.48rem 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.10);
            }

            .hero-stat-row:last-child { border-bottom: 0; }

            .hero-stat-label {
                color: rgba(255, 255, 255, 0.62) !important;
                font-size: 0.78rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }

            .hero-stat-value {
                color: #ffffff !important;
                font-weight: 800;
                text-align: right;
            }

            .workflow-step-grid {
                display: grid;
                grid-template-columns: repeat(6, minmax(0, 1fr));
                gap: 0.7rem;
                margin: 0.7rem 0 1.15rem 0;
            }

            .workflow-step-card {
                min-height: 174px;
                border: 1px solid var(--line);
                border-radius: 20px;
                padding: 0.9rem;
                background: var(--surface-glass);
                box-shadow: var(--shadow-card);
                position: relative;
                overflow: hidden;
            }

            .workflow-step-card::before {
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: var(--line-strong);
            }

            .workflow-step-complete::before { background: var(--teal); }
            .workflow-step-active::before { background: var(--gold); }
            .workflow-step-attention::before { background: var(--warning); }
            .workflow-step-locked { opacity: 0.62; }

            .workflow-step-topline {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.85rem;
            }

            .workflow-step-number {
                width: 2rem;
                height: 2rem;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border-radius: 999px;
                background: #e8f4f2;
                color: var(--teal-dark);
                font-weight: 850;
            }

            .workflow-status-pill {
                border-radius: 999px;
                background: #eef2f7;
                color: var(--ink-soft);
                padding: 0.25rem 0.48rem;
                font-size: 0.68rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }

            .workflow-step-title {
                color: var(--ink);
                font-weight: 850;
                font-size: 0.98rem;
                letter-spacing: -0.02em;
                margin-bottom: 0.18rem;
            }

            .workflow-step-eyebrow {
                color: var(--teal-dark);
                font-size: 0.72rem;
                font-weight: 780;
                text-transform: uppercase;
                letter-spacing: 0.07em;
                margin-bottom: 0.55rem;
            }

            .workflow-step-description,
            .workflow-step-helper {
                color: var(--muted);
                font-size: 0.82rem;
                line-height: 1.38;
            }

            .workflow-step-helper {
                margin-top: 0.65rem;
                font-weight: 700;
                color: var(--ink-soft);
            }

            .metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.75rem;
                margin: 0.75rem 0 1rem 0;
            }

            .metric-card {
                border: 1px solid var(--line);
                border-radius: 20px;
                padding: 1rem;
                background: var(--surface);
                box-shadow: var(--shadow-card);
            }

            .metric-card-label {
                color: var(--muted);
                font-size: 0.76rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 0.35rem;
            }

            .metric-card-value {
                color: var(--ink);
                font-size: 1.8rem;
                line-height: 1;
                font-weight: 880;
                letter-spacing: -0.04em;
            }

            .metric-card-helper {
                color: var(--muted);
                font-size: 0.82rem;
                margin-top: 0.45rem;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .panel-card,
            .section-card {
                border: 1px solid var(--line);
                border-radius: 24px;
                padding: 1.05rem 1.15rem;
                margin: 0.55rem 0 1rem 0;
                background: var(--surface-glass);
                box-shadow: var(--shadow-card);
            }

            .panel-card-title {
                color: var(--ink);
                font-size: 1.05rem;
                font-weight: 850;
                letter-spacing: -0.02em;
                margin-bottom: 0.25rem;
            }

            .panel-card-copy,
            .workflow-note {
                font-size: 0.92rem;
                color: var(--muted) !important;
                line-height: 1.5;
                margin-bottom: 0.75rem;
            }

            .quality-callout {
                border: 1px solid rgba(15, 155, 142, 0.28);
                border-radius: 18px;
                padding: 0.85rem 1rem;
                background: linear-gradient(135deg, rgba(15, 155, 142, 0.10), rgba(255, 255, 255, 0.78));
                color: var(--ink-soft) !important;
                margin: 0.65rem 0 1rem 0;
            }

            .sidebar-pill {
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 999px;
                padding: 0.34rem 0.62rem;
                margin: 0.24rem 0;
                font-size: 0.82rem;
                background: rgba(255, 255, 255, 0.08);
            }

            .project-action-note {
                font-size: 0.78rem;
                opacity: 0.72;
                line-height: 1.4;
                margin-top: 0.25rem;
                margin-bottom: 0.55rem;
            }

            .sidebar-review-card {
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 16px;
                padding: 0.72rem 0.82rem;
                margin: 0.45rem 0 0.8rem 0;
                background: rgba(255, 255, 255, 0.07);
            }

            .stButton > button,
            .stDownloadButton > button {
                border-radius: 999px !important;
                min-height: 2.72rem;
                font-weight: 780;
                border: 1px solid var(--line-strong) !important;
                box-shadow: 0 8px 20px rgba(15, 35, 55, 0.08);
            }

            .stButton > button[kind="primary"],
            .stDownloadButton > button[kind="primary"] {
                background: linear-gradient(135deg, var(--teal), var(--teal-dark)) !important;
                border: 0 !important;
                color: white !important;
            }

            div[data-testid="stTextArea"] textarea,
            div[data-testid="stTextInput"] input,
            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                border-radius: 16px !important;
                border-color: var(--line-strong) !important;
                background: rgba(255, 255, 255, 0.86) !important;
            }

            div[data-testid="stExpander"] {
                border-radius: 24px !important;
                border: 1px solid var(--line) !important;
                background: var(--surface-glass) !important;
                box-shadow: var(--shadow-card);
                overflow: hidden;
                margin-bottom: 1rem;
            }

            div[data-testid="stExpander"] details summary {
                font-weight: 840;
                color: var(--ink) !important;
                letter-spacing: -0.01em;
            }

            div[data-testid="stTabs"] button {
                font-weight: 750;
                color: var(--ink-soft);
            }

            [data-testid="stAlert"] {
                border-radius: 16px;
                border: 1px solid var(--line);
            }

            iframe[title="st.iframe"] {
                border-radius: 20px;
                box-shadow: var(--shadow-card);
            }

            @media (max-width: 1280px) {
                .workflow-step-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
                .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
                .app-hero-content { grid-template-columns: 1fr; }
            }

            @media (max-width: 760px) {
                .workflow-step-grid,
                .metric-grid { grid-template-columns: 1fr; }
                .app-hero { padding: 1.2rem; border-radius: 22px; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
