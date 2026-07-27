"""Activity inclusion summary helpers."""

import re

from text_polish import polish_title, polish_inclusion_items, polish_inclusion_item, strip_price_fragments
from itinerary_domain.field_sanitation import CustomerField, sanitize_customer_field, sanitize_customer_list

from itinerary_generation.content_engine import clean_client_title, merge_compound_inclusions, sanitize_inclusion_item
from itinerary_generation.inclusion_flat import clean_include_item
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from itinerary_generation.tallinn import clean_tallinn_ferry_inclusions, is_tallinn_ferry_framework, tallinn_ferry_title
from itinerary_generation.date_formatting import format_client_date
from .inclusion_utils import add_unique, clean


_SUPPLIER_SECTION_LABEL_RE = re.compile(
    r"^(?:what[’']?s included\??|what to expect\??|booking information|"
    r"please note|important information|supplier note|operator note|"
    r"duration|suitable for|age limit|gather at|meeting point)$",
    flags=re.IGNORECASE,
)

_SUPPLIER_SECTION_START_RE = re.compile(
    r"\b(?:what[’']?s included|what to expect|booking information|"
    r"please note|important information|supplier note|operator note)\b",
    flags=re.IGNORECASE,
)

_SUPPLIER_OPERATIONAL_INCLUSION_RE = re.compile(
    r"\b(?:booking flow|diet(?:ary)? restrictions?|food allergies|please fill in|"
    r"personally responsible|activity day|equipped and ready|"
    r"15\s*(?:min\.?|minutes?)\s+before\s+start|"
    r"wear clothes accordingly to weather|meeting point\s+15)\b",
    flags=re.IGNORECASE,
)

_FIRST_PERSON_MARKETING_RE = re.compile(
    r"\b(?:join us|we\s+(?:start|take|hike|go|eat|gather)|our\s+local\s+guide)\b",
    flags=re.IGNORECASE,
)

_NARRATIVE_FRAGMENT_RE = re.compile(
    r"^(?:close to\b|where\s+we\b|it[’']?s\s+time\s+to\b|we\s+gather\s+at\b|"
    r".+\bnational\s+park\s+is\s+located\s+\d+\b)",
    flags=re.IGNORECASE,
)

def _strip_supplier_tail(text: str) -> str:
    return _SUPPLIER_SECTION_START_RE.split(str(text or ""), maxsplit=1)[0].strip(" -:,;")


def _is_supplier_only_inclusion(text: str) -> bool:
    lower = str(text or "").lower().strip(" -:,;? .")
    if not lower:
        return True
    if _SUPPLIER_SECTION_LABEL_RE.match(lower):
        return True
    if _SUPPLIER_OPERATIONAL_INCLUSION_RE.search(lower):
        return True
    if _NARRATIVE_FRAGMENT_RE.search(lower):
        return True
    if _FIRST_PERSON_MARKETING_RE.search(lower) and len(lower.split()) > 8:
        return True
    return False


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
    text = polish_inclusion_item(sanitize_customer_field(strip_price_fragments(str(value or "").strip()), CustomerField.INCLUSION), title)
    text = re.split(r"\s+-\s+(?:Description|Overview)\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:")
    text = _strip_supplier_tail(text)
    lower = text.lower().strip(":? ")
    if not text:
        return ""
    if _is_supplier_only_inclusion(text):
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
    text = polish_inclusion_item(clean_include_item(sanitize_customer_field(text, CustomerField.INCLUSION), title), title)
    text = _strip_supplier_tail(text)
    if _is_supplier_only_inclusion(text):
        return ""
    return sanitize_inclusion_item(text, title)


def _fallback_activity_inclusions(row: dict, title: str) -> list[str]:
    source = " ".join(str(row.get(key, "") or "") for key in ["title", "original_title", "details", "includes"]).lower()
    if "fløibanen" in source or "floibanen" in source:
        items = ["Round-trip Fløibanen ticket"] if re.search(r"\bround[-\s]?trip\b|\broundtrip\b", source, flags=re.IGNORECASE) else ["Fløibanen ticket"]
        if "fløyen" in source or "floyen" in source or "mount" in source or "viewpoint" in source:
            items.append("Flexible visit to Mount Fløyen")
        return items
    if "icebreaker" in source and "cruise" in source:
        city = str(row.get("city", "") or "").strip()
        return [
            f"Shuttle bus from {city}" if city else "Shuttle bus transfer",
            "Icebreaker cruise",
            "Floating in icy Arctic waters in survival suits",
            "Walk on the frozen sea",
            "Complimentary hot drink",
            "Cruise & Swim certificate",
        ]
    return []


def _activity_inclusion_items(row: dict, title: str) -> list[str]:
    raw_items = row.get("includes", []) or []
    cleaned = []
    for item in raw_items:
        item = _polish_activity_inclusion(item, title)
        if item and item not in cleaned:
            cleaned.append(item)
    source_text = " ".join(str(row.get(key, "") or "") for key in ["title", "original_title", "details", "includes"]).lower()
    if "icebreaker" in source_text and "cruise" in source_text:
        cleaned = _fallback_activity_inclusions(row, title)
    elif not cleaned:
        cleaned = _fallback_activity_inclusions(row, title)
    merged = merge_compound_inclusions(polish_inclusion_items(cleaned, title))
    return [item for item in merged if item]


def activity_line(row: dict) -> str:
    if row.get("group_tour_optional_extra"):
        return ""
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
    title = sanitize_customer_field(title, CustomerField.TITLE)
    heading = sanitize_customer_field(f"{title} - {date}" if date else title, CustomerField.TITLE)
    inclusions = clean_tallinn_ferry_inclusions(row) if is_tallinn_ferry_framework(row) else _activity_inclusion_items(row, heading)
    inclusions = sanitize_customer_list(inclusions, CustomerField.INCLUSION)
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
    """Extract polished group-tour inclusions without leaking raw day headings.

    Supplier overviews often list both broad itinerary stages ("Day 1: Golden
    Circle") and true included activities ("Skaftafell glacier hike (3 h)").
    Keep concrete included activities; turn broad programme coverage into one
    polished summary instead of random heading fragments.
    """
    from itinerary_generation.group_tours import is_group_tour_overview

    items: list[str] = []
    programme_summaries: list[str] = []
    concrete_re = re.compile(r"\b(?:glacier\s+hike|boat\s+(?:ride|tour)|amphibian|ice\s+cave|katla|whale\s+watching|blue\s+lagoon\s+admission|entrance|admission)\b", flags=re.IGNORECASE)
    broad_heading_re = re.compile(r"\b(?:golden circle|south coast|eastfjords|north iceland|west iceland|blue lagoon|j[öo]kuls[áa]rl[óo]n)\b", flags=re.IGNORECASE)

    for row in rows:
        if not is_group_tour_overview(row):
            continue
        text = f'{row.get("title", "")}\n{row.get("original_title", "")}\n{row.get("details", "")}'
        lower_text = text.lower()
        places = []
        for label, patterns in [
            ("Golden Circle", ["golden circle", "þingvellir", "thingvellir", "geysir", "gullfoss"]),
            ("South Coast", ["south coast", "seljalandsfoss", "skógafoss", "skogafoss", "reynisfjara"]),
            ("Jökulsárlón", ["jökulsárlón", "jokulsarlon", "diamond beach"]),
            ("East Fjords", ["east fjords", "eastfjords", "egilsstaðir", "egilsstadir"]),
            ("North Iceland", ["north iceland", "mývatn", "myvatn", "akureyri", "dettifoss", "goðafoss", "godafoss"]),
            ("West Iceland", ["west iceland", "laugarbakki", "borgarnes", "hraunfossar"]),
            ("Blue Lagoon", ["blue lagoon"]),
        ]:
            if any(pattern in lower_text for pattern in patterns) and label not in places:
                places.append(label)
        duration = ""
        duration_match = re.search(r"\b(\d+)\s*[- ]?day\b", text, flags=re.IGNORECASE)
        if duration_match:
            duration = f"{duration_match.group(1)}-day "
        if places:
            coverage = places[0] if len(places) == 1 else ", ".join(places[:-1]) + f" and {places[-1]}"
            programme_summaries.append(f"Guided {duration}Iceland programme covering {coverage}")

        in_included = False
        prose = re.search(r"included activities such as (.+?)(?: are arranged|\.|$)", text, flags=re.IGNORECASE | re.DOTALL)
        if prose:
            for candidate in re.split(r",\s*|\s+and\s+", prose.group(1)):
                item = clean(candidate).strip(" .")
                if concrete_re.search(item):
                    add_unique(items, polish_title(item))

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
                continue
            match = re.match(r"Day\s*\d+(?:\s*-\s*\d+)?\s*:\s*(.+)$", line, flags=re.IGNORECASE)
            if not match:
                continue
            item = clean(match.group(1)).strip(" .")
            if not item or _GROUP_TOUR_ACTIVITY_SKIP_RE.search(item):
                continue
            if concrete_re.search(item):
                add_unique(items, polish_title(item))
            elif broad_heading_re.search(item):
                # Broad route heading: represented by the programme summary.
                continue

    if not items and programme_summaries:
        add_unique(items, programme_summaries[0])
    elif programme_summaries:
        # Keep the programme summary after concrete inclusions as a compact route
        # coverage note, without replacing high-value activity inclusions.
        add_unique(items, programme_summaries[0])
    return items
