"""App shell, header, and embedded editor frame styles."""

CSS = r"""
html, body, [data-testid="stAppViewContainer"] {
                background: var(--app-bg) !important;
                color: var(--ink) !important;
            }

            .block-container {
                max-width: min(100% - 2rem, 1600px);
                padding-top: 0.85rem;
                padding-bottom: 3.5rem;
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

.luxury-hero {
                position: relative;
                display: grid;
                grid-template-columns: minmax(0, 1.6fr) minmax(260px, 0.65fr);
                gap: 1rem;
                align-items: center;
                padding: 1rem 1.15rem;
                border-radius: 20px;
                background: linear-gradient(135deg, #0f172a 0%, #1e3a4a 68%, #115e59 130%);
                border: 1px solid rgba(255,255,255,0.16);
                box-shadow: 0 10px 28px rgba(17, 24, 39, 0.12);
                overflow: hidden;
            }

            .luxury-hero::after {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(90deg, rgba(255,255,255,.06), transparent 48%);
                pointer-events: none;
            }

            .luxury-hero-main,
            .hero-summary-card {
                position: relative;
                z-index: 1;
            }

            .hero-eyebrow,
            .section-kicker {
                color: #f2c66d !important;
                font-size: 0.72rem;
                font-weight: 900;
                letter-spacing: .14em;
                text-transform: uppercase;
                margin-bottom: .35rem;
            }

            .luxury-hero h1 {
                color: #ffffff !important;
                font-size: clamp(1.7rem, 2.7vw, 2.85rem);
                line-height: 1.02;
                margin: 0;
                max-width: 880px;
            }

            .luxury-hero p {
                color: #e6eff7 !important;
                max-width: 760px;
                margin: .55rem 0 0;
                font-size: .98rem;
                line-height: 1.45;
            }

            .hero-summary-card {
                align-self: end;
                background: rgba(255,255,255,0.14);
                border: 1px solid rgba(255,255,255,0.24);
                border-radius: 16px;
                padding: .65rem .8rem;
                backdrop-filter: blur(14px);
            }

            .hero-summary-card div {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                padding: .36rem 0;
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
                margin: .55rem 0 .8rem;
                padding: .35rem .7rem;
                border: 1px solid var(--line);
                border-radius: 999px;
                background: rgba(255,255,255,.78);
                color: var(--muted) !important;
                font-size: .78rem;
                font-weight: 750;
            }
"""
