import streamlit as st

from ui.styles import apply_global_styles
from app_modules.main_view import render_app
from app_modules.project_io import initialise_state


APP_VERSION = "2026-05-28 v36c65-content-pipeline-consolidation"


st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide",
)

apply_global_styles()
initialise_state()
render_app(APP_VERSION)
