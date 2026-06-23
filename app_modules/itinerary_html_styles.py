from ui.render_helpers import esc


def build_preview_style(colors, cover_theme, cover_background_data_uri):
    """Return the shared preview/PDF HTML style block."""
    return f"""
    <style>
        .preview-background {{
            --page-bg: {esc(colors['page_bg'])};
            --preview-bg: {esc(colors['preview_bg'])};
            --ink: {esc(colors['ink'])};
            --body: {esc(colors['body'])};
            --muted: {esc(colors['muted'])};
            --line: {esc(colors['line'])};
            --card: {esc(colors['card'])};
            --accent: {esc(colors['accent'])};
            --cover-ink: {esc(cover_theme['ink'])};
            --cover-muted: {esc(cover_theme['muted'])};
            --cover-accent: {esc(cover_theme['accent'])};
            --cover-bg-image: url("{esc(cover_background_data_uri)}");
            background: var(--preview-bg);
            padding: 32px 0 60px 0;
        }}

        .a4-page {{
            position: relative;
            width: 794px;
            min-height: 1123px;
            background: var(--page-bg);
            color: var(--ink);
            margin: 0 auto 32px auto;
            padding: 66px 64px;
            box-sizing: border-box;
            font-family: Georgia, 'Times New Roman', serif;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
            break-after: page;
            page-break-after: always;
            overflow: hidden;
        }}

        .cover-page {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 66px 72px;
            background-image: var(--cover-bg-image);
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
        }}

        .cover-main {{
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
        }}

        .cover-emblem {{
            width: 52px;
            height: 52px;
            border: 1px solid rgba(184,149,85,.72);
            border-radius: 50%;
            margin: 0 auto 15px auto;
            position: relative;
        }}

        .cover-emblem::before {{
            content: "✦";
            position: absolute;
            left: 0;
            right: 0;
            top: 13px;
            text-align: center;
            font-size: 18px;
            color: var(--cover-accent);
        }}

        .cover-destination-card {{
            margin: 20px auto 0 auto;
            padding-top: 0;
            max-width: 610px;
        }}

        .summary-page {{
            /* Fallback for preview; the element also receives an inline
               background-image so Streamlit keeps the seasonal artwork. */
            background-image:
                linear-gradient(rgba(244,239,232,.40), rgba(244,239,232,.40)),
                var(--cover-bg-image);
            background-size: cover, cover;
            background-position: center center, center center;
            background-repeat: no-repeat, no-repeat;
        }}

        .summary-page .glance-card,
        .summary-page .journey-arc {{
            background: rgba(255,255,255,.76);
            backdrop-filter: blur(1px);
            box-shadow: 0 10px 26px rgba(31,52,70,.06);
        }}

        .single-day-page {{
            display: flex;
            flex-direction: column;
        }}

        .single-day-page .day-section {{
            flex: 0 0 auto;
        }}

        .day-kicker {{
            font-family: Arial, sans-serif;
            font-size: 11px;
            line-height: 1.25;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--accent);
            font-weight: 700;
            margin-bottom: 14px;
        }}

        .day-kicker-symbol {{
            color: var(--accent);
            letter-spacing: 0.10em;
            margin: 0 8px;
        }}

        .day-visual-block {{
            margin: auto -64px -66px -64px;
            flex: 0 0 auto;
        }}


        .day-image-slot {{
            margin: 0;
            height: 410px;
            overflow: visible;
            flex: 0 0 410px;
            position: relative;
            border-top: 5px solid rgba(184,149,85,.96);
            box-shadow: none;
            box-sizing: border-box;
        }}

        .day-image-slot::before {{
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            height: 26px;
            background: linear-gradient(to bottom, rgba(244,239,232,.16), rgba(244,239,232,0));
            z-index: 1;
            pointer-events: none;
        }}

        .day-image-preview-img {{
            display: block;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center 25%;
        }}

        .cover-kicker {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--cover-muted);
            margin-bottom: 14px;
        }}

        .cover-title {{
            font-size: 58px;
            line-height: 1.02;
            font-weight: 700;
            color: var(--cover-ink);
            margin-bottom: 18px;
        }}

        .cover-subtitle {{
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
        }}

        .cover-rule {{
            width: 160px;
            height: 1px;
            background: var(--cover-accent);
            opacity: 0.55;
            margin: 24px auto 0 auto;
            position: relative;
        }}

        .cover-rule::after {{
            content: "";
            width: 7px;
            height: 7px;
            background: var(--cover-accent);
            position: absolute;
            left: 50%;
            top: -3px;
            transform: translateX(-50%) rotate(45deg);
        }}


        .cover-dates {{
            font-family: Georgia, serif;
            color: var(--cover-muted);
            font-size: 14px;
            line-height: 1.35;
            margin-top: 8px;
            text-align: center;
        }}

        .cover-destination-label {{
            font-family: Arial, sans-serif;
            font-size: 10px;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: var(--cover-accent);
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .cover-destinations {{
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
        }}

        .cover-route-line {{
            display: block;
            white-space: normal;
        }}

        .cover-destination-pair {{
            display: inline-block;
            white-space: nowrap;
        }}

        .glance-card,
        .journey-arc {{
            background: rgba(255,255,255,0.18);
            border: 1px solid var(--line);
            padding: 30px;
        }}

        .glance-card {{
            margin-bottom: 36px;
        }}

        .glance-title,
        .journey-title {{
            font-size: 30px;
            margin-bottom: 16px;
            color: var(--ink);
        }}

        .glance-title::after,
        .journey-title::after,
        .final-page-title::after {{
            content: "";
            display: block;
            width: 86px;
            height: 1px;
            background: var(--line);
            margin-top: 12px;
        }}

        .glance-row {{
            display: grid;
            grid-template-columns: 165px 1fr;
            gap: 18px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.45;
            padding: 8px 0;
            border-bottom: 1px solid var(--line);
        }}

        .glance-label {{
            font-weight: 700;
            color: var(--ink);
        }}

        .glance-value {{
            color: var(--body);
        }}

        .journey-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: var(--body);
        }}

        .journey-table th {{
            text-align: left;
            color: var(--ink);
            font-weight: 700;
            padding: 10px 8px;
            border-bottom: 1px solid var(--line);
        }}

        .journey-table td {{
            padding: 12px 8px;
            vertical-align: top;
            border-bottom: 1px solid var(--line);
            line-height: 1.45;
        }}

        .journey-days {{
            white-space: nowrap;
        }}

        .day-label {{
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 6px;
            color: var(--ink);
        }}

        .day-label.day-label-legacy {{
            display: none;
        }}

        .day-title {{
            font-size: 27px;
            font-weight: 500;
            margin-bottom: 14px;
            color: var(--ink);
        }}

        .city {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 20px;
        }}

        .single-day-page .city {{
            display: none;
        }}

        .intro {{
            font-size: 15px;
            line-height: 1.5;
            margin-bottom: 22px;
            color: var(--body);
        }}

        .content-block {{
            margin-bottom: 15px;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .premium-travel-card {{
            border: 1px solid rgba(31, 52, 70, 0.16);
            background: rgba(255, 255, 255, 0.34);
            border-radius: 16px;
            padding: 16px 18px 15px;
            margin: 18px 0 20px;
            box-shadow: 0 10px 24px rgba(31, 52, 70, 0.04);
        }}

        .premium-travel-kicker {{
            margin-top: 0;
            margin-bottom: 7px;
            color: var(--accent);
        }}

        .premium-travel-title {{
            font-size: 19px;
            line-height: 1.24;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 7px;
        }}

        .premium-travel-description {{
            color: var(--body);
            margin-bottom: 10px;
        }}

        .premium-travel-badges,
        .premium-travel-chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin: 7px 0 10px;
        }}

        .premium-travel-badge,
        .premium-travel-chip {{
            display: inline-flex;
            align-items: center;
            border: 1px solid rgba(31, 52, 70, 0.14);
            border-radius: 999px;
            padding: 3px 9px 4px;
            font-family: Arial, sans-serif;
            font-size: 10.5px;
            line-height: 1.25;
            color: var(--ink);
            background: rgba(255, 255, 255, 0.48);
        }}

        .premium-travel-chip-muted {{
            color: var(--muted);
        }}

        .premium-route-ribbon {{
            margin: 9px 0 12px;
            padding: 9px 11px;
            border-left: 3px solid var(--accent);
            background: rgba(31, 52, 70, 0.045);
            font-family: Arial, sans-serif;
            font-size: 12.2px;
            line-height: 1.35;
            letter-spacing: 0.01em;
            color: var(--ink);
        }}

        .premium-travel-timeline {{
            margin: 10px 0 11px;
        }}

        .premium-travel-timeline-item {{
            display: grid;
            grid-template-columns: 14px 1fr;
            column-gap: 8px;
            align-items: start;
            font-size: 12.8px;
            line-height: 1.35;
            color: var(--body);
            margin-bottom: 5px;
        }}

        .premium-travel-timeline-item span {{
            width: 7px;
            height: 7px;
            margin-top: 5px;
            border-radius: 50%;
            background: var(--accent);
            opacity: 0.82;
        }}

        .premium-linked-transfers {{
            margin-top: 8px;
            padding-top: 4px;
            border-top: 1px solid rgba(31, 52, 70, 0.12);
        }}

        .section-title {{
            font-family: Arial, sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-top: 15px;
            margin-bottom: 5px;
            color: var(--accent);
        }}

        .small-section {{
            margin-top: 10px;
        }}

        .body-text {{
            font-size: 13.5px;
            line-height: 1.38;
            color: var(--body);
            margin-bottom: 5px;
        }}

        .muted-note {{
            color: var(--muted);
        }}

        .ve-text-small-note {{
            font-family: Arial, sans-serif;
            font-size: 11.5px;
            line-height: 1.36;
            color: var(--muted);
        }}

        .ve-text-large {{
            font-size: 15.5px;
            line-height: 1.45;
        }}

        .ve-text-heading {{
            font-size: 20px;
            line-height: 1.22;
            font-weight: 700;
            color: var(--ink);
            margin-top: 10px;
            margin-bottom: 7px;
        }}

        .ve-text-subheading {{
            font-family: Arial, sans-serif;
            font-size: 11.5px;
            line-height: 1.3;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--accent);
            margin-top: 8px;
            margin-bottom: 5px;
        }}

        .ve-text-muted,
        .ve-color-muted {{
            color: var(--muted);
        }}

        .ve-text-accent {{
            color: var(--accent);
            font-weight: 700;
        }}

        .ve-color-accent {{
            color: #9a6a16;
        }}

        .ve-color-warning {{
            color: #7a1c1c;
            font-weight: 700;
        }}

        .ve-color-highlight {{
            box-shadow: inset 0 -0.58em 0 rgba(197, 138, 36, .22);
            border-radius: 3px;
        }}

        .ve-text-premium-callout {{
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 16px;
            line-height: 1.48;
            color: var(--accent);
            font-weight: 700;
        }}

        .ve-color-deep-teal {{
            color: #005f5b;
        }}

        .ve-color-soft-teal-highlight {{
            box-shadow: inset 0 -0.58em 0 rgba(0, 127, 121, .18);
            border-radius: 3px;
        }}

        .ve-font-georgia {{
            font-family: Georgia, 'Times New Roman', serif !important;
        }}

        .ve-font-arial {{
            font-family: Arial, Helvetica, sans-serif !important;
        }}

        .ve-font-times {{
            font-family: 'Times New Roman', Times, serif !important;
        }}

        .ve-font-courier {{
            font-family: 'Courier New', Courier, monospace !important;
        }}

        .ve-size-9 {{ font-size: 12px !important; line-height: 1.35 !important; }}
        .ve-size-10 {{ font-size: 13.3px !important; line-height: 1.36 !important; }}
        .ve-size-11 {{ font-size: 14.7px !important; line-height: 1.36 !important; }}
        .ve-size-12 {{ font-size: 16px !important; line-height: 1.36 !important; }}
        .ve-size-14 {{ font-size: 18.7px !important; line-height: 1.34 !important; }}
        .ve-size-16 {{ font-size: 21.3px !important; line-height: 1.32 !important; }}
        .ve-size-18 {{ font-size: 24px !important; line-height: 1.30 !important; }}

        .ve-spacing-compact {{
            margin-bottom: 4px !important;
        }}

        .ve-spacing-normal {{
            margin-bottom: 13px !important;
        }}

        .ve-note-block {{
            border-left: 3px solid rgba(197,138,36,.72);
            padding: 8px 10px;
            margin: 10px 0 14px;
            box-shadow: inset 0 0 0 999px rgba(255,255,255,.18);
        }}

        .ve-note-block .body-text {{
            margin-bottom: 0;
        }}

        .ve-divider-block {{
            margin: 14px 0 16px;
        }}

        .ve-divider {{
            height: 1px;
            line-height: 1px;
            border-top: 1px solid rgba(31,52,70,.20);
            background: transparent;
            overflow: hidden;
        }}

        .strong-line {{
            font-weight: 600;
        }}

        .meta-label {{
            font-family: Arial, sans-serif;
            font-weight: 700;
            font-size: 12px;
            color: var(--ink);
        }}

        .final-page-title {{
            font-size: 34px;
            margin-bottom: 22px;
            color: var(--ink);
        }}

        .activity-inclusion-block {{
            margin-bottom: 18px;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .activity-inclusion-title {{
            font-size: 18px;
            line-height: 1.25;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 6px;
        }}

        ul {{
            margin-top: 5px;
            margin-bottom: 13px;
            padding-left: 21px;
        }}

        li {{
            font-size: 13.5px;
            line-height: 1.36;
            margin-bottom: 3px;
            color: var(--body);
        }}

        .final-list li {{
            margin-bottom: 5px;
        }}

        .inclusion-category-block {{
            margin-bottom: 20px;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .inclusion-category-block .section-title {{
            margin-top: 0;
            font-size: 12px;
        }}

        .inclusion-category-list li {{
            margin-bottom: 6px;
            line-height: 1.4;
        }}

        .inclusion-entry {{
            margin: 0 0 12px 0;
        }}

        .inclusion-entry-title {{
            margin-bottom: 2px;
        }}

        .inclusion-multiline-list {{
            margin-bottom: 8px;
        }}

        .inclusion-multiline-list .inclusion-entry-title {{
            display: block;
            margin-bottom: 2px;
        }}

        .inclusion-entry-detail {{
            color: var(--muted);
            margin-bottom: 0;
        }}

        .inclusion-multiline-list .inclusion-entry-detail {{
            display: block;
        }}

        .inclusion-entry-spacer {{
            height: 8px;
            line-height: 8px;
        }}

        .important-notes-page .note-paragraph {{
            font-size: 13.2px;
            line-height: 1.48;
            margin-bottom: 0;
        }}

        .notes-block {{
            margin-top: 8px;
        }}

        .premium-notes-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            background: transparent;
            border: 0;
            padding: 0;
        }}

        .premium-note-card {{
            border: 1px solid rgba(31, 52, 70, 0.15);
            background: rgba(255, 255, 255, 0.36);
            border-radius: 14px;
            padding: 13px 14px 12px;
            min-height: 82px;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .premium-note-card-title {{
            font-family: Arial, sans-serif;
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--accent);
            margin-bottom: 6px;
        }}

        @media print {{
            @page {{
                size: A4 portrait;
                margin: 0;
            }}

            .preview-background {{
                background: white;
                padding: 0;
            }}

            .a4-page {{
                width: 210mm;
                height: 297mm;
                min-height: 297mm;
                margin: 0;
                box-shadow: none;
                break-after: page;
                page-break-after: always;
            }}
        }}
    </style>

"""
