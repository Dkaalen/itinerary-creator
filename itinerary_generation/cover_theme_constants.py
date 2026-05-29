"""Static cover-theme labels and palettes."""

from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
COVER_BACKGROUND_DIR = APP_ROOT / "assets" / "cover_backgrounds"

SEASON_LABELS = {
    "winter": "Winter",
    "spring": "Spring",
    "summer": "Summer",
    "autumn": "Autumn",
}

SEASON_ORDER = ["automatic", "winter", "spring", "summer", "autumn"]

SEASON_SUBTITLES = {
    "winter": "A premium Nordic winter journey with scenic travel and Arctic experiences",
    "spring": "A premium spring journey with scenic travel and curated experiences",
    "summer": "A premium summer journey with scenic travel and curated experiences",
    "autumn": "A premium autumn journey with scenic travel and curated experiences",
}

SEASON_TITLES = {
    "winter": "Nordic Winter Journey",
    "spring": "Nordic Spring Journey",
    "summer": "Nordic Summer Journey",
    "autumn": "Nordic Autumn Journey",
}

SEASON_TEXT_COLORS = {
    "winter": {"ink": "#1f3446", "muted": "#7b746c", "accent": "#b89555"},
    "spring": {"ink": "#2e563f", "muted": "#7b7a66", "accent": "#b99a58"},
    "summer": {"ink": "#2c5a42", "muted": "#747865", "accent": "#b99a58"},
    "autumn": {"ink": "#35513f", "muted": "#7e6f5b", "accent": "#bb8b45"},
}
