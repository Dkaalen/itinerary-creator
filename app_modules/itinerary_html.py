import json

from generator import (
    create_destinations_line,
    create_journey_arc,
    create_trip_glance,
    create_trip_subtitle,
    create_trip_title,
    create_whats_included,
    create_whats_not_included,
)
from ui.day_rendering import (
    create_optional_addons,
    esc,
    get_important_travel_notes,
    render_day_pages,
    render_optional_addons_pages,
    render_split_list_pages,
    render_text_paragraph_page,
    text_to_list,
)
from app_modules.display_settings import get_color_preset, get_color_preset_name


def build_itinerary_html(parsed_rows, grouped_days, output_edits=None):
    output_edits = output_edits or {}
    preset_name = get_color_preset_name(output_edits)
    colors = get_color_preset(output_edits)
    colors_json = esc(json.dumps(colors))

    trip_title = output_edits.get("trip_title") or create_trip_title(parsed_rows, grouped_days)
    trip_subtitle = output_edits.get("trip_subtitle") or create_trip_subtitle(parsed_rows, grouped_days)
    destinations_line = output_edits.get("destinations_line") or create_destinations_line(parsed_rows)
    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    journey_arc = create_journey_arc(grouped_days)

    if output_edits.get("whats_included_text"):
        whats_included = text_to_list(output_edits.get("whats_included_text"))
    else:
        whats_included = create_whats_included(parsed_rows, grouped_days)

    optional_addons = create_optional_addons(parsed_rows)
    if output_edits.get("whats_not_included_text"):
        whats_not_included = text_to_list(output_edits.get("whats_not_included_text"))
    else:
        whats_not_included = create_whats_not_included()

    important_travel_notes = get_important_travel_notes(output_edits)

    html_text = f"""
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
            background: var(--preview-bg);
            padding: 32px 0 60px 0;
        }}

        .a4-page {{
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
            justify-content: center;
        }}

        .single-day-page {{
            display: flex;
            flex-direction: column;
        }}

        .single-day-page .day-section {{
            flex: 0 0 auto;
        }}

        .day-image-slot {{
            margin: auto -64px -66px -64px;
            height: 410px;
            overflow: hidden;
            flex: 0 0 410px;
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
            font-size: 13px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 18px;
        }}

        .cover-title {{
            font-size: 54px;
            line-height: 1.05;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 18px;
        }}

        .cover-subtitle {{
            font-size: 24px;
            line-height: 1.25;
            color: var(--ink);
            margin-bottom: 18px;
        }}

        .cover-destinations {{
            font-family: Arial, sans-serif;
            font-size: 15px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--body);
            margin-top: 24px;
        }}

        .glance-card,
        .journey-arc {{
            background: var(--card);
            border: 1px solid var(--line);
            padding: 28px;
        }}

        .glance-card {{
            margin-bottom: 34px;
        }}

        .glance-title,
        .journey-title {{
            font-size: 30px;
            margin-bottom: 16px;
            color: var(--ink);
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

        .day-title {{
            font-size: 27px;
            font-weight: 500;
            margin-bottom: 12px;
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

        .packed-day-page {{
            padding-top: 46px;
            padding-bottom: 46px;
        }}

        .packed-section .day-label {{
            font-size: 34px;
            margin-bottom: 4px;
        }}

        .packed-section .day-title {{
            font-size: 27px;
            line-height: 1.16;
            margin-bottom: 8px;
        }}

        .packed-section .city {{
            font-size: 12px;
            margin-bottom: 10px;
        }}

        .packed-section .intro {{
            font-size: 15px;
            line-height: 1.42;
            margin-bottom: 12px;
        }}

        .packed-section .content-block {{
            margin-bottom: 8px;
        }}

        .packed-section .section-title {{
            font-size: 11px;
            margin-top: 9px;
            margin-bottom: 3px;
        }}

        .packed-section .body-text,
        .packed-section li {{
            font-size: 13.5px;
            line-height: 1.32;
            margin-bottom: 2px;
        }}

        .packed-section ul {{
            margin-top: 3px;
            margin-bottom: 6px;
            padding-left: 17px;
        }}

        .day-separator {{
            height: 1px;
            background: var(--line);
            margin: 16px 0 13px 0;
        }}

        .triple-day-page {{
            padding-top: 38px;
            padding-bottom: 38px;
        }}

        .triple-day-page .day-separator {{
            margin: 9px 0 8px 0;
        }}

        .triple-packed-section .day-label {{
            font-size: 34px;
            margin-bottom: 3px;
        }}

        .triple-packed-section .day-title {{
            font-size: 27px;
            line-height: 1.16;
            margin-bottom: 7px;
        }}

        .triple-packed-section .city {{
            font-size: 12px;
            margin-bottom: 8px;
        }}

        .triple-packed-section .intro {{
            font-size: 15px;
            line-height: 1.38;
            margin-bottom: 9px;
        }}

        .triple-packed-section .content-block {{
            margin-bottom: 5px;
        }}

        .triple-packed-section .section-title {{
            font-size: 11px;
            margin-top: 7px;
            margin-bottom: 2px;
        }}

        .triple-packed-section .body-text,
        .triple-packed-section li {{
            font-size: 13.5px;
            line-height: 1.30;
            margin-bottom: 1px;
        }}

        .triple-packed-section ul {{
            margin-top: 2px;
            margin-bottom: 4px;
            padding-left: 15px;
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

        .important-notes-page .note-paragraph {{
            font-size: 14px;
            line-height: 1.55;
            margin-bottom: 14px;
        }}

        .notes-block {{
            margin-top: 8px;
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

    <div class="preview-background" data-preset="{esc(preset_name)}" data-colors="{colors_json}">

        <div class="a4-page cover-page">
            <div class="cover-kicker">Curated Travel Itinerary</div>
            <div class="cover-title">{esc(trip_title)}</div>
            <div class="cover-subtitle">{esc(trip_subtitle)}</div>
            <div class="cover-destinations">{esc(destinations_line)}</div>
        </div>

        <div class="a4-page">
            <div class="glance-card">
                <div class="glance-title">Your Trip at a Glance</div>
    """

    for label, value in trip_glance.items():
        html_text += f"""
                <div class="glance-row">
                    <div class="glance-label">{esc(label)}</div>
                    <div class="glance-value">{esc(value)}</div>
                </div>
        """

    html_text += """
            </div>

            <div class="journey-arc">
                <div class="journey-title">Your Journey Arc</div>
                <table class="journey-table">
                    <thead>
                        <tr>
                            <th>Chapter</th>
                            <th>Days</th>
                            <th>What You’ll Experience</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for chapter in journey_arc:
        html_text += f"""
                        <tr>
                            <td>{esc(chapter["chapter"])}</td>
                            <td class="journey-days">{esc(chapter["days"])}</td>
                            <td>{esc(chapter["experience"])}</td>
                        </tr>
        """

    html_text += """
                    </tbody>
                </table>
            </div>
        </div>
    """

    html_text += render_day_pages(grouped_days, output_edits)

    html_text += render_split_list_pages("What’s included", whats_included)
    html_text += render_optional_addons_pages(optional_addons)
    html_text += render_split_list_pages("What’s not included", whats_not_included)
    html_text += render_text_paragraph_page("Important travel notes", important_travel_notes)

    html_text += "</div>"

    return html_text
