"""Parse meal-plan values from supplier accommodation text."""

from parser_modules.common import clean_space


MEAL_PLAN_MARKERS = ("breakfast", "brekafast", "meal", "dinner", "half board", "full board", "room only", "self catering", "self-catering")
COMMA_MEAL_PLAN_MARKERS = ("incl", *MEAL_PLAN_MARKERS)


def parse_meal_plan(value):
    text = clean_space(value); lower = text.lower()
    if not text: return ""
    if ("without" in lower or "no " in lower or "not included" in lower or "not incl" in lower) and ("breakfast" in lower or "brekafast" in lower): return "without breakfast"
    if "breakfast" in lower or "brekafast" in lower: return "breakfast and dinner" if "dinner" in lower else "breakfast"
    if "half board" in lower or "half-board" in lower: return "half board"
    if "full board" in lower or "full-board" in lower: return "full board"
    if "room only" in lower: return "room only"
    if "self catering" in lower or "self-catering" in lower: return "self catering"
    if "dinner" in lower: return "dinner"
    return ""


def is_meal_plan_part(part_lower, *, comma_format=False):
    markers = COMMA_MEAL_PLAN_MARKERS if comma_format else MEAL_PLAN_MARKERS
    return any(marker in part_lower for marker in markers)
