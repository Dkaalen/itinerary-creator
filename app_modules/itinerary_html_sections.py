from ui.render_helpers import esc
from itinerary_generation.cover_assets import cover_focus_css_position


def balanced_cover_subtitle_html(subtitle: str) -> str:
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


def render_cover_page(
    *,
    cover_theme: dict,
    cover_background_path: str,
    cover_crop_focus: str,
    cover_kicker: str,
    cover_title_class: str,
    trip_title: str,
    trip_subtitle_html: str,
    trip_dates: str,
    destinations_line_html: str,
) -> str:
    """Render the cover page section for the itinerary preview/PDF HTML."""
    background_position = cover_focus_css_position(cover_crop_focus)
    return f"""        <div class="a4-page cover-page cover-season-{esc(cover_theme['season'])}" data-cover-season="{esc(cover_theme['season'])}" data-cover-background-path="{esc(cover_background_path)}" data-cover-crop-focus="{esc(cover_crop_focus)}" data-cover-ink="{esc(cover_theme['ink'])}" data-cover-muted="{esc(cover_theme['muted'])}" data-cover-accent="{esc(cover_theme['accent'])}" style="background-position: {esc(background_position)};">
            <div class="cover-main">
                <div class="cover-emblem" aria-hidden="true"></div>
                <div class="cover-kicker">{esc(cover_kicker)}</div>
                <div class="{esc(cover_title_class)}">{esc(trip_title)}</div>
                <div class="cover-subtitle">{trip_subtitle_html}</div>
                {f'<div class="cover-dates">{esc(trip_dates)}</div>' if trip_dates else ''}
                <div class="cover-rule"></div>
                <div class="cover-destination-card">
                    <div class="cover-destination-label">Route</div>
                    <div class="cover-destinations">{destinations_line_html}</div>
                </div>
            </div>
        </div>

"""


def render_summary_page(
    *,
    cover_theme: dict,
    trip_glance: dict,
    journey_arc: list[dict],
    summary_background_data_uri: str = "",
    summary_background_path: str = "",
    summary_crop_focus: str = "top",
) -> str:
    """Render the trip glance and journey arc summary page."""
    background_position = cover_focus_css_position(summary_crop_focus)
    background_style = (
        f"background-image: linear-gradient(rgba(244,239,232,.40), rgba(244,239,232,.40)), url('{esc(summary_background_data_uri)}'); "
        f"background-position: center center, {esc(background_position)};"
        if summary_background_data_uri
        else f"background-position: center center, {esc(background_position)};"
    )
    html_text = f"""        <div class="a4-page summary-page cover-season-{esc(cover_theme['season'])}" data-cover-season="{esc(cover_theme['season'])}" data-cover-background-path="{esc(summary_background_path)}" data-cover-crop-focus="{esc(summary_crop_focus)}" style="{background_style}">
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
    return html_text
