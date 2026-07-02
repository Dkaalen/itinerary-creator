"""Responsive Streamlit layout styles."""

CSS = r"""
@media (max-width: 980px) {
    .metric-grid { grid-template-columns: 1fr 1fr; }
}

@media (max-width: 620px) {
    .metric-grid { grid-template-columns: 1fr; }
    .block-container {
        max-width: min(100% - .8rem, 1880px) !important;
        width: min(100% - .8rem, 1880px) !important;
    }
}
"""
