"""Shared constants used by the Streamlit app UI."""

from app_modules.output_brand import BOOKNORDICS_COLORS


COLOR_PRESETS = {
    "Classic Agent": {
        "page_bg": "#f4efe8",
        "preview_bg": "#11151b",
        "ink": "#1f3446",
        "body": "#2f2f2f",
        "muted": "#7b746c",
        "line": "#d8cec2",
        "card": "rgba(255, 255, 255, 0.34)",
        "accent": "#1f3446",
    },
    "Booknordics B2C": BOOKNORDICS_COLORS,
}

PRESET_ORDER = list(COLOR_PRESETS.keys())

DETAIL_LEVELS = [
    "Rich descriptive",
]

DEFAULT_IMPORTANT_TRAVEL_NOTES = [
    "Transport schedules, including flights, trains, buses, ferries and cruises, are subject to operational changes. Final confirmed timings will be provided in the travel vouchers.",
    "Activities may be weather dependent and can be adjusted if required for safety, availability or operational reasons.",
    "Northern Lights sightings are a natural phenomenon and cannot be guaranteed. Tours are arranged to give the best possible opportunity based on local conditions.",
    "Hotel check-in and check-out times vary by property. As a general guideline, check-in in the Nordic region is usually between 3:00 PM and 4:30 PM, while check-out is usually between 10:00 AM and 12:00 noon.",
    "Route, road and rail conditions in the Nordic region can vary in winter. Please follow local guidance and allow extra time for independent transfers.",
    "Some transfers are self-arranged unless specifically listed as included. Please allow enough time between hotels, stations, airports and meeting points, especially during winter conditions.",
]
