import streamlit as st

from ui.styles import apply_global_styles
from app_modules.main_view import render_app
from app_modules.workflow_state import ensure_workflow_defaults
from app_modules.app_version import APP_VERSION


st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide",
)

apply_global_styles()
ensure_workflow_defaults(st.session_state)
render_app(APP_VERSION)
