"""Cover-page preview/PDF styles."""

CSS = r"""
.cover-page {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 66px 72px;
            background-image: var(--cover-bg-image);
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
        }

        .cover-main {
            position: absolute;
            top: 70px;
            left: 0;
            right: 0;
            transform: none;
            width: auto;
            max-width: none;
            margin: 0 auto;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .cover-emblem {
            width: 52px;
            height: 52px;
            border: 1px solid rgba(184,149,85,.72);
            border-radius: 50%;
            margin: 0 auto 15px auto;
            position: relative;
        }

        .cover-emblem::before {
            content: "✦";
            position: absolute;
            left: 0;
            right: 0;
            top: 13px;
            text-align: center;
            font-size: 18px;
            color: var(--cover-accent);
        }

        .cover-destination-card {
            margin: 20px auto 0 auto;
            padding-top: 0;
            max-width: 610px;
        }

.cover-kicker {
            font-family: Arial, sans-serif;
            font-size: 12px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--cover-muted);
            margin-bottom: 14px;
        }

        .cover-title {
            font-size: 58px;
            line-height: 1.02;
            font-weight: 700;
            color: var(--cover-ink);
            margin-bottom: 18px;
        }

        .cover-subtitle {
            display: block;
            width: 610px;
            max-width: calc(100% - 144px);
            font-size: 22px;
            line-height: 1.28;
            color: var(--cover-ink);
            margin: 0 auto;
            padding-left: 0;
            padding-right: 0;
            text-align: center !important;
            text-wrap: balance;
            align-self: center;
        }

        .cover-rule {
            width: 160px;
            height: 1px;
            background: var(--cover-accent);
            opacity: 0.55;
            margin: 24px auto 0 auto;
            position: relative;
        }

        .cover-rule::after {
            content: "";
            width: 7px;
            height: 7px;
            background: var(--cover-accent);
            position: absolute;
            left: 50%;
            top: -3px;
            transform: translateX(-50%) rotate(45deg);
        }


        .cover-dates {
            font-family: Georgia, serif;
            color: var(--cover-muted);
            font-size: 14px;
            line-height: 1.35;
            margin-top: 8px;
            text-align: center;
        }

        .cover-destination-label {
            font-family: Arial, sans-serif;
            font-size: 10px;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: var(--cover-accent);
            margin-bottom: 10px;
            font-weight: 700;
        }

        .cover-destinations {
            font-family: Arial, sans-serif;
            font-size: 13px;
            line-height: 1.45;
            letter-spacing: 0.075em;
            text-transform: uppercase;
            color: var(--cover-ink);
            max-width: 640px;
            margin: 0 auto;
            text-align: center;
            text-wrap: normal;
        }

        .cover-route-line {
            display: block;
            white-space: normal;
        }

        .cover-destination-pair {
            display: inline-block;
            white-space: nowrap;
        }
"""
