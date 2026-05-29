"""Activity inclusion summary helpers."""

import re

from text_polish import polish_title

from itinerary_generation.content_engine import clean_client_title
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from .inclusion_utils import add_unique, clean


def activity_line(row: dict) -> str:
    title = create_client_activity_title(row) or row.get("title", "")
    title = clean_client_title(title, row) or title
    if "norway in a nutshell" in str(title).lower():
        return polish_title(title)
    return normalize_client_day_title(title, row)


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
