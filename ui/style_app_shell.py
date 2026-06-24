"""App shell, header, and embedded editor frame styles."""

CSS = r"""
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
"""
