"""Direct PDF export and download station styles."""

CSS = r"""

.export-readiness-panel {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin: .8rem 0 1rem;
    padding: 1rem 1.1rem;
    border: 1px solid rgba(199, 208, 202, .76);
    border-radius: 22px;
    background: rgba(255, 253, 248, .86);
    box-shadow: var(--shadow-card);
}

.export-readiness-copy {
    min-width: 0;
}

.export-readiness-copy span {
    display: block;
    color: var(--teal-dark) !important;
    font-size: .68rem;
    font-weight: 900;
    letter-spacing: .12em;
    text-transform: uppercase;
}

.export-readiness-copy strong {
    display: block;
    color: var(--ink) !important;
    font-size: 1.04rem;
    font-weight: 900;
    margin-top: .12rem;
}

.export-readiness-copy p {
    color: var(--ink-soft) !important;
    margin: .16rem 0 0;
}

.export-readiness-chips {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: .42rem;
}

.export-readiness-chips span {
    color: var(--ink-soft) !important;
    font-size: .74rem;
    font-weight: 760;
    border: 1px solid rgba(199, 208, 202, .70);
    background: rgba(248, 245, 238, .82);
    border-radius: 999px;
    padding: .28rem .52rem;
}

@media (max-width: 740px) {
    .export-readiness-panel {
        align-items: flex-start;
        flex-direction: column;
    }
    .export-readiness-chips {
        justify-content: flex-start;
    }
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
"""
