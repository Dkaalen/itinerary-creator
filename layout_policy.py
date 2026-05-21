"""Layout policy for itinerary day pages.

v36 moves the product direction toward a premium visual layout where each day is
treated as its own A4 design unit. Keeping this policy separate makes it harder
for older smart-packing logic to reappear in the UI or renderer by accident.
"""

DEFAULT_DAY_PAGE_LAYOUT = "One day per page"
DAY_PAGE_LAYOUTS = [DEFAULT_DAY_PAGE_LAYOUT]

# Older project JSON files may still contain these values. They are recognized
# only so they can be normalized safely back to the current default.
LEGACY_DAY_PAGE_LAYOUTS = {
    "Smart compact pages",
    "3-days per page",
    DEFAULT_DAY_PAGE_LAYOUT,
}


def normalize_day_page_layout(value=None):
    """Return the only supported day layout for the current premium PDF mode."""
    return DEFAULT_DAY_PAGE_LAYOUT


def is_day_packing_enabled(value=None):
    """Day packing is intentionally disabled for the v36 visual layout path."""
    return False


def is_three_day_packing_enabled(value=None):
    """Three-day packing is intentionally disabled for the v36 visual layout path."""
    return False
