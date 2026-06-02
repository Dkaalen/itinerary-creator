"""Activity inclusion summary helpers."""

import re

from text_polish import polish_title, polish_inclusion_items, polish_inclusion_item, strip_price_fragments

from itinerary_generation.content_engine import clean_client_title, merge_compound_inclusions, sanitize_inclusion_item
from itinerary_generation.inclusion_flat import clean_include_item
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.tallinn import clean_tallinn_ferry_inclusions, is_tallinn_ferry_framework, tallinn_ferry_title
from itinerary_generation.date_formatting import format_client_date
from .inclusion_utils import add_unique, clean


def _looks_like_descriptive_prose(text: str) -> bool:
    lower = str(text or "").lower()
    prose_markers = [
        "tour gives",
        "take a stroll",
        "listen to",
        "make sense",
        "to top it all",
        "waterworld",
        "best way to understand",
        "explore bergen from",
        "historic city streets",
        "what to expect",
        "overview",
    ]
    return len(str(text or "")) > 95 and any(marker in lower for marker in prose_markers)


def _polish_activity_inclusion(value: str, title: str = "") -> str:
    text = polish_inclusion_item(strip_price_fragments(str(value or "").strip()), title)
    text = re.split(r"\s+-\s+(?:Description|Overview)\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:")
    lower = text.lower().strip(":? ")
    if not text:
        return ""
    if lower in {"what's included", "what’s included", "includes", "included", "description", "overview"}:
        return ""
    if re.search(r"^not\s+in(?:cl|lc)uded\b|^excluded\b", lower, flags=re.IGNORECASE):
        return ""
    if re.search(r"\b(price|cost|supplement)\b", lower, flags=re.IGNORECASE) and re.search(r"\b(per person|per passenger|eur|nok|usd|gbp|dkk|sek|isk|kr|€|\$|£|\d)\b", lower, flags=re.IGNORECASE):
        return ""
    if "included excluded" in lower or "food and drinks are excluded" in lower:
        return ""
    if _looks_like_descriptive_prose(text):
        return ""
    if len(text) > 150 and "included" not in lower:
        return ""
    text = polish_inclusion_item(clean_include_item(text, title), title)
    return sanitize_inclusion_item(text, title)


def _activity_inclusion_items(row: dict, title: str) -> list[str]:
    raw_items = row.get("includes", []) or []
    cleaned = []
    for item in raw_items:
        item = _polish_activity_inclusion(item, title)
        if item and item not in cleaned:
            cleaned.append(item)
    merged = merge_compound_inclusions(polish_inclusion_items(cleaned, title))
    return [item for item in merged if item]


def activity_line(row: dict) -> str:
    if is_tallinn_ferry_framework(row):
        title = tallinn_ferry_title(row)
    else:
        title = create_client_activity_title(row) or row.get("title", "")
        title = clean_client_title(title, row) or title
    if "norway in a nutshell" in str(title).lower():
        title = polish_title(title)
    else:
        title = normalize_client_day_title(title, row)

    date = format_client_date(row.get("start_date"))
    heading = f"{title} - {date}" if date else title
    inclusions = clean_tallinn_ferry_inclusions(row) if is_tallinn_ferry_framework(row) else _activity_inclusion_items(row, heading)
    if inclusions:
        return f"{heading}\n{', '.join(inclusions)}"
    return heading


_GROUP_TOUR_ACTIVITY_SKIP_RE = re.compile(
    r"\b(?:hotel|guesthouse|accommodation|w/\s*breakfast|with breakfast|breakfast|pick\W*up|return to|arrival\b)\b",
    flags=re.IGNORECASE,
)

_GROUP_TOUR_ACTIVITY_KEEP_RE = re.compile(
    r"\b(?:glacier hike|amphibian|boat ride|boat tour|ice cave|katla|whale watching|golden circle|waterfall|reynisfjara|diamond beach|j[öo]kuls[áa]rl[óo]n|skaftafell|eastfjords|fishing villages|dettifoss|m[ýy]vatn|go[ðd]afoss)\b",
    flags=re.IGNORECASE,
)


def group_tour_overview_activity_lines(rows: list[dict]) -> list[str]:
    """Extract meaningful included group-tour activities from supplier overview rows."""
    items: list[str] = []
    for row in rows:
        text = f'{row.get("title", "")}\n{row.get("original_title", "")}\n{row.get("details", "")}'
        in_included = False
        for raw in text.replace("–", "-").splitlines():
            line = clean(raw).strip(" •-*|:")
            if not line:
                continue
            lower = line.lower()
            if lower in {"what's included?", "what’s included?", "what's included", "what’s included"}:
                in_included = True
                continue
            if lower.startswith(("not included", "what to expect", "overview", "please note")):
                if not lower.startswith("overview"):
                    in_included = False
                continue
            if not in_included:
                # Also catch compact prose summaries such as "included activities such as...".
                prose = re.search(r"included activities such as (.+?)(?: are arranged|\.|$)", line, flags=re.IGNORECASE)
                if prose:
                    candidates = re.split(r",\s*|\s+and\s+", prose.group(1))
                    for candidate in candidates:
                        candidate = clean(candidate).strip(" .")
                        if candidate.lower().startswith("and "):
                            candidate = candidate[4:].strip()
                        if _GROUP_TOUR_ACTIVITY_KEEP_RE.search(candidate):
                            add_unique(items, polish_title(candidate))
                continue
            match = re.match(r"Day\s*\d+(?:\s*-\s*\d+)?\s*:\s*(.+)$", line, flags=re.IGNORECASE)
            if not match:
                continue
            item = clean(match.group(1)).strip(" .")
            if not item or _GROUP_TOUR_ACTIVITY_SKIP_RE.search(item):
                continue
            if _GROUP_TOUR_ACTIVITY_KEEP_RE.search(item):
                item = re.sub(r"\bvisit\b", "", item, flags=re.IGNORECASE).strip(" ,.-")
                add_unique(items, polish_title(item))
    return items
