"""
layout_policy.py

Central layout policy for the visual itinerary path.

The current v36 layout standard is one itinerary day per A4 page. Older layout
names are accepted and normalized so saved project/session state cannot bring
back compact multi-day pages when image placement is enabled.
"""

DEFAULT_DAY_PAGE_LAYOUT = "One day per page"
DAY_PAGE_LAYOUTS = [DEFAULT_DAY_PAGE_LAYOUT]

LEGACY_DAY_PAGE_LAYOUTS = {
    "Smart compact pages",
    "3-days per page",
    "One day per page",
}


def normalize_day_page_layout(value=None):
    value = str(value or "").strip()
    if value == DEFAULT_DAY_PAGE_LAYOUT:
        return DEFAULT_DAY_PAGE_LAYOUT
    if value in LEGACY_DAY_PAGE_LAYOUTS:
        return DEFAULT_DAY_PAGE_LAYOUT
    return DEFAULT_DAY_PAGE_LAYOUT


def is_day_packing_enabled(value=None):
    return False


def is_three_day_packing_enabled(value=None):
    return False
