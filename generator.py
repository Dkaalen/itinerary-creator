from collections import defaultdict


def group_rows_by_day(parsed_rows):
    """
    Groups parsed itinerary rows by day.
    Example:
    Day 1 -> Arrival, Transfer, Hotel
    Day 2 -> Activity
    """

    grouped = defaultdict(list)

    for row in parsed_rows:
        day = row.get("day", "Unknown day")
        grouped[day].append(row)

    return dict(grouped)


def create_day_title(day_rows):
    """
    Creates a simple day title based on the most important row.
    This is an early version.
    """

    priority_order = ["Activity", "Transfer", "Hotel", "Arrival", "Departure", "Leisure"]

    for item_type in priority_order:
        for row in day_rows:
            if row.get("type") == item_type:
                return row.get("title", "Day at leisure")

    return "Day at leisure"