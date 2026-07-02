"""Normal itinerary workflow and content panel styles."""

CSS = r"""
.flow-nav,
.document-stage-panel {
    display: none !important;
}

.bottom-cta {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    padding: 1rem 1.1rem;
    box-shadow: var(--shadow-card);
    margin-top: 1rem;
}

.bottom-cta {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.bottom-cta strong,
.panel-card-title {
    color: var(--ink) !important;
    font-weight: 850;
}

.bottom-cta span,
.workflow-step-helper,
.workflow-step-description,
.workflow-note,
.project-action-note {
    color: var(--ink-soft) !important;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .75rem;
    margin: 1rem 0;
}

.metric-card,
.workflow-step-card,
.quality-callout {
    background: var(--paper);
    color: var(--ink) !important;
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    padding: .95rem;
    box-shadow: var(--shadow-card);
}

.metric-card-label,
.workflow-step-eyebrow {
    color: var(--teal-dark) !important;
    font-weight: 820;
    text-transform: uppercase;
    letter-spacing: .10em;
    font-size: .72rem;
}

.metric-card-value,
.workflow-step-title {
    color: var(--ink) !important;
    font-weight: 850;
    font-size: 1.05rem;
}
"""
