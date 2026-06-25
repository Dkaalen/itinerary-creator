"""Shared constants used by the Streamlit app UI."""

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
    "Booknordics B2C": {
        "page_bg": "#F7F9FB",
        "preview_bg": "#07111F",
        "ink": "#111827",
        "body": "#1F2937",
        "muted": "#64748B",
        "line": "#D9E1EA",
        "card": "rgba(255, 255, 255, 0.82)",
        "accent": "#F2055C",
    },
}

PRESET_ORDER = list(COLOR_PRESETS.keys())

DETAIL_LEVELS = [
    "Rich descriptive",
]

DEFAULT_IMPORTANT_TRAVEL_NOTES = [
    "Transport schedules, including flights, trains, buses, ferries and cruises, are subject to operational changes. Final confirmed timings will be provided in the travel vouchers.",
    "Activities may be weather dependent and can be adjusted if required for safety, availability or operational reasons.",
    "Hotel check-in and check-out times vary by property. As a general guideline, check-in in the Nordic region is usually between 3:00 PM and 4:30 PM, while check-out is usually between 10:00 AM and 12:00 noon.",
]
