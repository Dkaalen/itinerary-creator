"""App shell, header, and embedded editor frame styles."""

CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
                background: var(--app-bg) !important;
                color: var(--ink) !important;
            }

            .block-container {
                max-width: none;
                width: min(100vw, 100%);
                padding: 0.75rem 1.5rem 3.5rem;
            }

            h1, h2, h3, h4, h5, h6 {
                color: var(--ink) !important;
                letter-spacing: -0.025em;
            }

            p, li, label, [data-testid="stMarkdownContainer"] {
                color: var(--ink-soft) !important;
            }

            label, [data-testid="stWidgetLabel"] p {
                color: var(--ink) !important;
                font-weight: 750 !important;
            }

.luxury-hero {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 1rem;
                align-items: center;
                padding: .75rem 1rem;
                border-radius: 14px;
                background: #ffffff;
                border: 1px solid var(--line);
                box-shadow: var(--shadow-card);
                overflow: hidden;
            }

            .compact-app-header {
                margin-bottom: .75rem;
            }

            .hero-eyebrow,
            .section-kicker {
                color: var(--teal-dark) !important;
                font-size: .72rem;
                font-weight: 900;
                letter-spacing: .12em;
                text-transform: uppercase;
                margin-bottom: .2rem;
            }

            .luxury-hero h1 {
                color: var(--ink) !important;
                font-size: clamp(1.15rem, 1.5vw, 1.55rem);
                line-height: 1.15;
                margin: 0;
                max-width: 720px;
            }

            .luxury-hero p {
                color: var(--muted) !important;
                max-width: 820px;
                margin: .22rem 0 0;
                font-size: .88rem;
                line-height: 1.35;
            }

            .hero-summary-card {
                min-width: 330px;
                background: var(--surface-soft);
                border: 1px solid var(--line);
                border-radius: 12px;
                padding: .45rem .65rem;
            }

            .hero-summary-card div {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                padding: .22rem 0;
                border-bottom: 1px solid rgba(100, 116, 139, 0.18);
            }

            .hero-summary-card div:last-child { border-bottom: 0; }
            .hero-summary-card span {
                color: var(--muted) !important;
                font-size: .68rem;
                text-transform: uppercase;
                letter-spacing: .10em;
                font-weight: 850;
            }
            .hero-summary-card strong {
                color: var(--ink) !important;
                text-align: right;
                font-weight: 850;
                font-size: .82rem;
            }

            .app-version-pill { display: none; }
"""
