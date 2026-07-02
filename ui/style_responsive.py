"""Responsive Streamlit layout styles."""

CSS = r"""
@media (max-width: 980px) {
                .luxury-hero { grid-template-columns: 1fr; }
                .hero-summary-card { min-width: 0; }
                .flow-nav { grid-template-columns: 1fr 1fr; }
                .metric-grid { grid-template-columns: 1fr 1fr; }
            }

            @media (max-width: 620px) {
                .flow-nav { grid-template-columns: 1fr; }
                .metric-grid { grid-template-columns: 1fr; }
                .block-container { padding-left: .75rem; padding-right: .75rem; }
            }
"""
