"""Detect supplier group-tour overview rows."""


def is_group_tour_overview(row: dict) -> bool:
    text = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    return (row.get("effective_type") == "Day Overview" or row.get("type") == "Day Overview") and any(marker in text for marker in ("group tour", "holiday package", "what's included", "what’s included"))
