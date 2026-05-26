"""Shared Streamlit styling for the internal itinerary app."""

import streamlit as st


def apply_global_styles():
    st.markdown(
        """
        <style>
            .block-container { padding-top: 2rem; }
            div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 { margin-top: 0.25rem; }
            .app-hero {
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 18px;
                padding: 1.1rem 1.25rem;
                background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
                margin-bottom: 1rem;
            }
            .app-hero h1 { margin-bottom: 0.2rem; }
            .app-hero p { margin-bottom: 0; opacity: 0.82; }
            .section-card {
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 16px;
                padding: 1rem;
                margin: 0.5rem 0 1rem 0;
                background: rgba(255,255,255,0.025);
            }
            .workflow-note {
                font-size: 0.9rem;
                opacity: 0.76;
                margin-bottom: 0.7rem;
            }
            .sidebar-pill {
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 999px;
                padding: 0.28rem 0.55rem;
                margin: 0.18rem 0;
                font-size: 0.82rem;
                background: rgba(255,255,255,0.035);
            }
            .project-action-note {
                font-size: 0.78rem;
                opacity: 0.72;
                line-height: 1.35;
                margin-top: 0.25rem;
                margin-bottom: 0.5rem;
            }
            .sidebar-review-card {
                border: 1px solid rgba(148, 163, 184, 0.24);
                border-radius: 14px;
                padding: 0.72rem 0.82rem;
                margin: 0.45rem 0 0.8rem 0;
                background: linear-gradient(135deg, rgba(255,255,255,0.07), rgba(255,255,255,0.025));
            }
            .sidebar-review-card strong { font-size: 0.92rem; }
            .stButton > button, .stDownloadButton > button {
                border-radius: 999px !important;
                min-height: 2.55rem;
                font-weight: 650;
            }
            div[data-testid="stExpander"] {
                border-radius: 16px !important;
                border-color: rgba(148, 163, 184, 0.25) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
