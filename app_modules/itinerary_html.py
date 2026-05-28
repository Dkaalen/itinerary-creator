import json

from itinerary_generation.inclusions import create_whats_included, create_whats_not_included
from itinerary_generation.inclusion_sections import create_categorized_inclusions
from itinerary_generation.summaries import create_journey_arc, create_trip_glance
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title
from itinerary_generation.cover_theme import get_cover_theme
from ui.day_pages import (
    render_day_pages,
    render_split_list_pages,
    render_categorized_inclusions_pages,
    render_custom_html_final_page,
    render_text_paragraph_page,
)
from ui.final_pages import (
    create_optional_addons,
    get_important_travel_notes,
    render_optional_addons_pages,
)
from ui.render_helpers import esc, text_to_list
from app_modules.display_settings import get_color_preset, get_color_preset_name


def _balanced_cover_subtitle_html(subtitle: str) -> str:
    """Return escaped cover subtitle HTML with a gentle line break to avoid orphan words."""
    text = str(subtitle or "").strip()
    if not text:
        return ""

    def escaped(value: str) -> str:
        return esc(" ".join(value.split()))

    if len(text) < 62 or " " not in text:
        return escaped(text)

    candidates = []
    for marker in [", ", " and "]:
        start = 0
        while True:
            idx = text.find(marker, start)
            if idx == -1:
                break
            split_at = idx + (1 if marker == ", " else 0)
            left = text[:split_at].strip()
            right = text[split_at:].strip(" ,")
            if len(left) >= 28 and len(right) >= 18:
                candidates.append((abs(len(left) - 58), left, right))
            start = idx + 1

    if not candidates:
        words = text.split()
        best = None
        for i in range(4, len(words) - 2):
            left = " ".join(words[:i])
            right = " ".join(words[i:])
            if len(right) >= 18:
                candidate = (abs(len(left) - 58), left, right)
                best = candidate if best is None or candidate[0] < best[0] else best
        if best:
            _, left, right = best
            return f"{escaped(left)}<br>{escaped(right)}"
        return escaped(text)

    _, left, right = sorted(candidates)[0]
    return f"{escaped(left)}<br>{escaped(right)}"


def build_itinerary_html(parsed_rows, grouped_days, output_edits=None):
    output_edits = output_edits or {}
    preset_name = get_color_preset_name(output_edits)
    colors = get_color_preset(output_edits)
    colors_json = esc(json.dumps(colors))

    cover_theme = get_cover_theme(parsed_rows, output_edits)
    cover_kicker = output_edits.get("cover_kicker") or "Curated Travel Itinerary"
    trip_title = output_edits.get("trip_title") or create_trip_title(parsed_rows, grouped_days)
    cover_title_class = "cover-title"
    if len(str(trip_title)) <= 24:
        cover_title_class += " cover-title-fit"
    elif len(str(trip_title)) <= 32:
        cover_title_class += " cover-title-balanced"
    trip_subtitle = output_edits.get("trip_subtitle") or create_trip_subtitle(parsed_rows, grouped_days)
    trip_subtitle_html = _balanced_cover_subtitle_html(trip_subtitle)
    cover_background_data_uri = cover_theme.get("background_data_uri", "")
    cover_background_path = cover_theme.get("background_path", "")
    destinations_line = output_edits.get("destinations_line") or create_destinations_line(parsed_rows)
    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    saved_trip_glance = output_edits.get("trip_glance") or {}
    if isinstance(saved_trip_glance, dict):
        for label, value in saved_trip_glance.items():
            if label in trip_glance:
                trip_glance[label] = value

    saved_journey_arc = output_edits.get("journey_arc")
    if isinstance(saved_journey_arc, list) and saved_journey_arc:
        journey_arc = [
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": str(row.get("experience", "")).strip(),
            }
            for row in saved_journey_arc
            if isinstance(row, dict)
        ]
    else:
        journey_arc = create_journey_arc(grouped_days)

    manual_whats_included = text_to_list(output_edits.get("whats_included_text", ""))
    categorized_inclusions = create_categorized_inclusions(parsed_rows, grouped_days)
    whats_included = manual_whats_included or create_whats_included(parsed_rows, grouped_days)

    optional_addons = create_optional_addons(parsed_rows)
    if output_edits.get("whats_not_included_text"):
        whats_not_included = text_to_list(output_edits.get("whats_not_included_text"))
    else:
        whats_not_included = create_whats_not_included(parsed_rows)

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
            left: 50%;
            transform: translateX(-50%);
            width: 610px;
            max-width: calc(100% - 144px);
            margin: 0;
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
            color: var(--cover-accent);
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
            width: 100%;
            max-width: 500px;
            font-size: 22px;
            line-height: 1.28;
            color: var(--cover-ink);
            margin: 0 auto;
            text-align: center;
            text-wrap: balance;
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
            font-size: 14px;
            line-height: 1.45;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--cover-ink);
            max-width: 720px;
            margin: 0 auto;
            text-align: center;
            text-wrap: balance;
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

        <div class="a4-page cover-page cover-season-{esc(cover_theme['season'])}" data-cover-season="{esc(cover_theme['season'])}" data-cover-background-path="{esc(cover_background_path)}">
            <div class="cover-main">
                <div class="cover-emblem" aria-hidden="true"></div>
                <div class="cover-kicker">{esc(cover_kicker)}</div>
                <div class="{esc(cover_title_class)}">{esc(trip_title)}</div>
                <div class="cover-subtitle">{trip_subtitle_html}</div>
                <div class="cover-rule"></div>
                <div class="cover-destination-card">
                    <div class="cover-destination-label">Route</div>
                    <div class="cover-destinations">{esc(destinations_line)}</div>
                </div>
            </div>
        </div>

        <div class="a4-page summary-page cover-season-{esc(cover_theme['season'])}" style="background-image: linear-gradient(rgba(244,239,232,.40), rgba(244,239,232,.40)), url('{esc(cover_background_data_uri)}'); background-size: cover, cover; background-position: center center, center center; background-repeat: no-repeat, no-repeat;" data-cover-season="{esc(cover_theme['season'])}" data-cover-background-path="{esc(cover_background_path)}">
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

    if output_edits.get("whats_included_html"):
        html_text += render_custom_html_final_page("What’s included", output_edits.get("whats_included_html"), "final-list-page categorized-inclusions-page")
    elif manual_whats_included:
        html_text += render_split_list_pages("What’s included", whats_included)
    else:
        html_text += render_categorized_inclusions_pages("What’s included", categorized_inclusions)
    html_text += render_optional_addons_pages(optional_addons)
    html_text += render_split_list_pages("What’s not included", whats_not_included)
    html_text += render_text_paragraph_page("Important travel notes", important_travel_notes)

    html_text += "</div>"

    return html_text
