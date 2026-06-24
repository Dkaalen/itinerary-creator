"""Day-page itinerary content preview/PDF styles."""

CSS = r"""
.single-day-page {
            display: flex;
            flex-direction: column;
        }

        .single-day-page .day-section {
            flex: 0 0 auto;
        }

        .day-kicker {
            font-family: Arial, sans-serif;
            font-size: 11px;
            line-height: 1.25;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--accent);
            font-weight: 700;
            margin-bottom: 14px;
        }

        .day-kicker-symbol {
            color: var(--accent);
            letter-spacing: 0.10em;
            margin: 0 8px;
        }

.day-label {
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 6px;
            color: var(--ink);
        }

        .day-label.day-label-legacy {
            display: none;
        }

        .day-title {
            font-size: 27px;
            font-weight: 500;
            margin-bottom: 14px;
            color: var(--ink);
        }

        .city {
            font-family: Arial, sans-serif;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 20px;
        }

        .single-day-page .city {
            display: none;
        }

        .intro {
            font-size: 15px;
            line-height: 1.5;
            margin-bottom: 22px;
            color: var(--body);
        }

        .content-block {
            margin-bottom: 15px;
            break-inside: avoid;
            page-break-inside: avoid;
        }

        .premium-notes-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            background: transparent;
            border: 0;
            padding: 0;
        }

        .premium-note-card {
            border: 1px solid rgba(31, 52, 70, 0.15);
            background: rgba(255, 255, 255, 0.36);
            border-radius: 14px;
            padding: 13px 14px 12px;
            min-height: 82px;
            break-inside: avoid;
            page-break-inside: avoid;
        }

        .premium-note-card-title {
            font-family: Arial, sans-serif;
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--accent);
            margin-bottom: 6px;
        }
"""
