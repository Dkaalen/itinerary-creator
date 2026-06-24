"""Summary and journey-table preview/PDF styles."""

CSS = r"""
.summary-page {
            /* Fallback for preview; the element also receives an inline
               background-image so Streamlit keeps the seasonal artwork. */
            background-image:
                linear-gradient(rgba(244,239,232,.40), rgba(244,239,232,.40)),
                var(--cover-bg-image);
            background-size: cover, cover;
            background-position: center center, center center;
            background-repeat: no-repeat, no-repeat;
        }

        .summary-page .glance-card,
        .summary-page .journey-arc {
            background: rgba(255,255,255,.76);
            backdrop-filter: blur(1px);
            box-shadow: 0 10px 26px rgba(31,52,70,.06);
        }

.glance-card,
        .journey-arc {
            background: rgba(255,255,255,0.18);
            border: 1px solid var(--line);
            padding: 30px;
        }

        .glance-card {
            margin-bottom: 36px;
        }

        .glance-title,
        .journey-title {
            font-size: 30px;
            margin-bottom: 16px;
            color: var(--ink);
        }

        .glance-title::after,
        .journey-title::after {
            content: "";
            display: block;
            width: 86px;
            height: 1px;
            background: var(--line);
            margin-top: 12px;
        }

        .glance-row {
            display: grid;
            grid-template-columns: 165px 1fr;
            gap: 18px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.45;
            padding: 8px 0;
            border-bottom: 1px solid var(--line);
        }

        .glance-label {
            font-weight: 700;
            color: var(--ink);
        }

        .glance-value {
            color: var(--body);
        }

        .journey-table {
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: var(--body);
        }

        .journey-table th {
            text-align: left;
            color: var(--ink);
            font-weight: 700;
            padding: 10px 8px;
            border-bottom: 1px solid var(--line);
        }

        .journey-table td {
            padding: 12px 8px;
            vertical-align: top;
            border-bottom: 1px solid var(--line);
            line-height: 1.45;
        }

        .journey-days {
            white-space: nowrap;
        }
"""
