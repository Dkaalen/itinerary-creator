"""Normal itinerary workflow and content panel styles."""

CSS = r"""
.flow-nav {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: .75rem;
                margin: 0 0 1.4rem;
            }

            .flow-nav-item {
                display: flex;
                align-items: center;
                gap: .7rem;
                padding: .9rem 1rem;
                border-radius: 20px;
                border: 1px solid var(--line);
                background: #ffffff;
                box-shadow: 0 8px 20px rgba(16,32,51,.05);
            }

            .flow-nav-item span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 2rem;
                height: 2rem;
                border-radius: 999px;
                font-weight: 900;
                background: #e7f4f2;
                color: var(--teal-dark) !important;
            }

            .flow-nav-item strong {
                color: var(--ink) !important;
                font-size: .96rem;
            }

            .flow-nav-current {
                border-color: rgba(0,127,121,.46);
                box-shadow: 0 12px 26px rgba(0,127,121,.12);
            }

            .flow-nav-current span {
                background: var(--teal-dark);
                color: #ffffff !important;
            }

            .flow-nav-done span {
                background: #dff7ed;
                color: #087443 !important;
            }

            .flow-nav-locked {
                background: #f8fafc;
            }

            .document-stage-panel,
            .bottom-cta {
                background: rgba(255,255,255,.92);
                border: 1px solid var(--line);
                border-radius: 26px;
                padding: 1.2rem 1.25rem;
                box-shadow: var(--shadow-card);
                margin-bottom: 1rem;
            }

            .document-stage-panel h2 {
                margin: 0;
                font-size: clamp(1.45rem, 2.4vw, 2.15rem);
            }

            .document-stage-panel p {
                margin: .55rem 0 0;
                color: var(--ink-soft) !important;
                max-width: 820px;
            }

            .bottom-cta {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 1.25rem;
                background: #fffdf8;
                border-color: rgba(0,127,121,.22);
            }

            .bottom-cta strong {
                display: block;
                color: var(--ink) !important;
                font-size: 1.05rem;
            }

            .bottom-cta span {
                display: block;
                color: var(--ink-soft) !important;
                margin-top: .2rem;
            }

            .metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: .8rem;
                margin: 1rem 0;
            }

            .metric-card,
            .workflow-step-card,
            .quality-callout {
                background: #ffffff;
                color: var(--ink) !important;
                border: 1px solid var(--line);
                border-radius: 22px;
                padding: 1rem;
                box-shadow: var(--shadow-card);
            }

            .metric-card-label,
            .workflow-step-eyebrow {
                color: var(--teal-dark) !important;
                font-weight: 900;
                text-transform: uppercase;
                letter-spacing: .10em;
                font-size: .74rem;
            }
            .metric-card-value,
            .workflow-step-title {
                color: var(--ink) !important;
                font-weight: 900;
                font-size: 1.2rem;
            }
            .metric-card-helper,
            .workflow-step-helper,
            .workflow-step-description,
            .workflow-note,
            .project-action-note {
                color: var(--ink-soft) !important;
            }

            .panel-card-title { color: var(--ink) !important; font-weight: 900; }

            [data-testid="stExpander"] {
                border-radius: 22px !important;
                border: 1px solid var(--line) !important;
                background: #ffffff !important;
                box-shadow: var(--shadow-card) !important;
            }

            iframe[title="visual_page_editor"] {
                border-radius: 28px !important;
                border: 1px solid var(--line) !important;
                box-shadow: var(--shadow-soft) !important;
                background: #fffdf8 !important;
            }
"""
