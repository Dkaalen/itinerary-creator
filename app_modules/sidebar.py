"""Compatibility shim for the removed sidebar workflow."""


def get_current_itinerary_state():
    return [], {}


def get_itinerary_stats(parsed_rows=None, grouped_days=None):
    return {
        "days": 0,
        "destinations": 0,
        "destination_names": [],
        "activities": 0,
        "hotels": 0,
        "self_arranged": 0,
        "optional_rows": 0,
    }


def make_title_suggestions(parsed_rows, grouped_days):
    return []


def build_review_items(parsed_rows=None, grouped_days=None):
    return []


def get_itinerary_health(review_items):
    return "Excellent"


def render_sidebar_review_assistant(parsed_rows, grouped_days, stats):
    return None


def render_sidebar(app_version):
    return None
