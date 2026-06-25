"""Static labels and ordering for what's-not-included sections."""

DEFAULT_WHATS_NOT_INCLUDED_ITEMS = [
    "International flights unless specifically listed",
    "Meals unless specifically stated",
    "Drinks unless specifically stated",
    "Porterage unless specified",
    "Self transfers and self-arranged travel costs unless specifically stated",
    "Travel insurance",
    "Optional extras and personal expenses",
    "Optional experiences unless specifically confirmed",
    "City taxes or local fees, where applicable",
]

EXCLUSION_SECTION_ORDER = [
    ("self_arranged_flights", "Self-arranged flights"),
    ("self_transfers", "Self transfers"),
    ("optional_experiences", "Optional experiences"),
    ("optional_transfers", "Optional transfers"),
    ("optional_hotels", "Optional hotels/add-ons"),
    ("costs_not_included", "Activity-specific exclusions"),
]
