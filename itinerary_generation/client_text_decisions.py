"""Shared meaning-based decisions for client-facing itinerary text.

This module keeps the small wording decisions used by day intros, Journey Arc,
and late output validation in one place.  The goal is not to generate prose from
random phrases, but to make the same context decision everywhere:

* meaningful activity context wins over logistics;
* destination-only travel/check-in days become ``Welcome to <destination>``;
* real scenic routes may describe the route;
* generic connection/filler wording is never considered a valid experience.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Iterable, Sequence

from itinerary_generation.common import get_primary_city, get_row_type, has_hotel


@dataclass(frozen=True)
class TextRule:
    """A simple marker-driven text decision."""

    markers: tuple[str, ...]
    template: Callable[[str, str], str]

    def matches(self, text: str) -> bool:
        return any(marker in text for marker in self.markers)

    def render(self, title: str, city: str) -> str:
        return self.template(title, city)


def _normalise_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _contains(text: str, *markers: str) -> bool:
    return any(marker in text for marker in markers)


ACTIVITY_INTRO_RULES: tuple[TextRule, ...] = (
    TextRule(
        ("oslofjord", "electric boat", "trollcruise"),
        lambda title, city: f"Begin with Oslo from the water, where {title} adds harbour views, island scenery and an easy fjord perspective to the capital stay.",
    ),
    TextRule(
        ("lysefjord", "preikestolen", "pulpit rock"),
        lambda title, city: f"The day centres on Lysefjord, with {title} carrying you from Stavanger beneath steep mountain walls, waterfalls and the viewpoint of Preikestolen.",
    ),
    TextRule(
        ("otra river",),
        lambda title, city: f"See Kristiansand from river level today, with {title} giving the day a quiet outdoor rhythm through the city’s waterways.",
    ),
    TextRule(
        ("bergen past & present", "fløibanen", "floibanen"),
        lambda title, city: f"Bergen comes into focus through local stories, old harbour streets and viewpoints, with {title} giving the day both city context and mountain perspective.",
    ),
    TextRule(
        ("icebreaker", "survival suit", "frozen sea", "cruise & swim"),
        lambda title, city: f"Today includes a distinctive Arctic sea experience, with {title} arranged from {city} and time on the frozen water built into the day.",
    ),
    TextRule(
        ("kayak", "kayaking", "paddle"),
        lambda title, city: f"Today you explore {city} from the water on {title}, with peaceful scenery and local guidance shaping the experience.",
    ),
    TextRule(
        ("food tour", "cuisine", "culinary", "taste"),
        lambda title, city: f"Taste your way through {city} on {title}, combining local food stops with hidden city corners and stories from your guide.",
    ),
    TextRule(
        ("walking", "city highlights", "suomenlinna"),
        lambda title, city: f"Walk through {city} with {title}, using local stories, historic streets and lesser-known corners to give the destination more context.",
    ),
    TextRule(
        ("northern lights", "aurora"),
        lambda title, city: "The day is kept easy around your evening Northern Lights experience, giving you time to settle before heading out with local guidance after dark.",
    ),
    TextRule(
        ("fjord", "cruise", "boat", "silent electric ship"),
        lambda title, city: f"Sail from {city} on {title}, with fjord scenery, coastal landmarks and time on the water shaping the day.",
    ),
    TextRule(
        ("funicular", "cable car", "fjellheisen", "fløibanen", "floibanen"),
        lambda title, city: f"Use today for a flexible viewpoint visit in {city}, with {title} arranged so you can choose the timing that suits the day.",
    ),
    TextRule(
        ("santa", "reindeer", "husky"),
        lambda title, city: f"Today focuses on classic Arctic experiences around {city}, with animal encounters or seasonal activities arranged at an easy pace.",
    ),
    TextRule(
        ("blue lagoon", "volcano"),
        lambda title, city: "Today combines Icelandic landscapes with time to unwind, balancing the volcano area and Blue Lagoon in one arranged day.",
    ),
    TextRule(
        ("photo", "sommar", "landscape"),
        lambda title, city: f"Set out from {city} for a scenery-led experience, with the route shaped around light, weather and the best viewpoints of the day.",
    ),
)


GROUP_TOUR_INTRO_RULES: tuple[TextRule, ...] = (
    TextRule(
        ("golden circle",),
        lambda title, city: "The guided route moves into the Golden Circle today, combining Þingvellir, Geysir and Gullfoss with the first overnight stop outside Reykjavík.",
    ),
    TextRule(
        ("south coast", "katla"),
        lambda title, city: "Continue along Iceland’s South Coast, where waterfalls, black-sand scenery and the Katla Ice Cave shape the main part of the day.",
    ),
    TextRule(
        ("jökuls", "jokuls", "diamond beach", "skaftafell"),
        lambda title, city: "Glacier scenery leads the day, with Skaftafell, Jökulsárlón and Diamond Beach forming the main stops before the next overnight stay.",
    ),
    TextRule(
        ("eastfjord", "egils"),
        lambda title, city: "The route turns through the Eastfjords today, with fishing villages, mountain roads and local landscapes giving this stage a quieter pace.",
    ),
    TextRule(
        ("north iceland", "mývatn", "myvatn", "dettifoss"),
        lambda title, city: "Travel into North Iceland, with waterfall stops, geothermal landscapes and the Mývatn area giving the day its main focus.",
    ),
    TextRule(
        ("whale", "hauganes"),
        lambda title, city: "Your guided route returns towards Reykjavík today, with time on the water for whale watching before the programme comes back to the capital.",
    ),
)


WEAK_JOURNEY_ARC_RE = re.compile(
    r"(?:"
    r"\bflight\s+connection\b|"
    r"\b(?:scenic\s+)?travel\s+connection\b|"
    r"\bonward\s+(?:flight|train|travel|connection|connections)\b|"
    r"\btravel\s+arrangements\b|"
    r"\baccommodation\s+as\s+listed\b|"
    r"\barrival\s+arrangements\b|"
    r"\btravel\s+continues\b|"
    r"\bcontinue\s+your\s+journey\s+with\s+arranged\s+travel\b"
    r")",
    flags=re.IGNORECASE,
)


SCENIC_ROUTE_MARKERS = (
    "norway in a nutshell",
    "flåm",
    "flam",
    "nærøyfjord",
    "naeroyfjord",
    "bergen railway",
    "flåm railway",
    "flam railway",
    "scenic rail",
    "fjord cruise",
    "coastal cruise",
)


def client_activity_intro(activity_title: str, city: str, source_text: str = "", *, compact: bool = False) -> str:
    """Return one shared activity-day intro used by all day-intro paths."""

    title = _normalise_text(activity_title) or "the arranged experience"
    city_text = _normalise_text(city) or "the destination"
    searchable = f"{title} {source_text}".lower()
    for rule in ACTIVITY_INTRO_RULES:
        if rule.matches(searchable):
            return rule.render(title, city_text)
    if compact:
        return f"{title} is the main arranged experience in {city_text}, with the rest of the day kept flexible."
    return f"{title} is the main arranged experience in {city_text}, with the rest of the day kept simple and easy to follow."


def client_group_tour_intro(activity_title: str, city: str, source_text: str = "") -> str:
    """Return one shared intro for guided group-tour continuation days."""

    title = _normalise_text(activity_title) or "today's guided route"
    city_text = _normalise_text(city) or "the route"
    searchable = f"{title} {source_text}".lower()
    for rule in GROUP_TOUR_INTRO_RULES:
        if rule.matches(searchable):
            return rule.render(title, city_text)
    return f"The guided programme continues through {city_text} today, with the main stops, route and overnight arrangements handled as part of the tour."


def welcome_arc_phrase(chapter: str = "") -> str:
    chapter = _normalise_text(chapter)
    if chapter and chapter.lower() not in {"journey", "cruise", "route"}:
        return f"Welcome to {chapter}"
    return "Arrival and time to settle in"


def is_weak_journey_arc_phrase(text: object) -> bool:
    value = _normalise_text(text)
    return not value or bool(WEAK_JOURNEY_ARC_RE.search(value))


def sanitize_journey_arc_phrase(text: object, *, chapter: str = "") -> str:
    """Clean stale or generated weak Journey Arc copy.

    This is used by summaries, render/PDF output, the visual editor, and the
    quality gate so those paths cannot drift into different wording standards.
    """

    value = _normalise_text(text)
    if not value:
        return welcome_arc_phrase(chapter) if chapter else "Time to explore at your own pace"
    value = re.sub(r"\bAurora\b", "Northern Lights", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+(?:and|&)\s+onward\s+(?:train|flight|travel|connections?)\b.*$", "", value, flags=re.IGNORECASE).strip(" ,")
    value = re.sub(r"\bonward\s+(?:train|flight|travel|connections?)\b", "", value, flags=re.IGNORECASE).strip(" ,")
    value = _normalise_text(value).strip(" ,")
    if is_weak_journey_arc_phrase(value):
        return welcome_arc_phrase(chapter)
    return value or welcome_arc_phrase(chapter)


def is_scenic_route_text(text: object) -> bool:
    value = str(text or "").lower()
    return _contains(value, *SCENIC_ROUTE_MARKERS)


def _rows_text(rows: Iterable[dict]) -> str:
    return " ".join(
        " ".join(
            [
                str(row.get("city", "")),
                str(row.get("title", "")),
                str(row.get("original_title", "")),
                str(row.get("details", "")),
                " ".join(row.get("includes", []) or []),
            ]
        )
        for row in rows or []
        if isinstance(row, dict)
    ).lower()


def has_meaningful_activity(rows: Iterable[dict]) -> bool:
    return any(
        get_row_type(row) == "Activity" and (row.get("effective_type") or row.get("type")) == "Activity"
        for row in rows or []
    )


def is_destination_logistics_only(rows: Sequence[dict] | Iterable[dict]) -> bool:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    if not row_list:
        return False
    if has_meaningful_activity(row_list):
        return False
    row_types = {get_row_type(row) for row in row_list}
    if not row_types:
        return False
    logistics_types = {"Hotel", "Transfer", "Flight", "Train", "Transport", "Cruise", "Ferry", "Arrival", "Departure"}
    return row_types.issubset(logistics_types) and (has_hotel(row_list) or "Arrival" in row_types or "Departure" in row_types)


def destination_logistics_phrase(rows: Sequence[dict] | Iterable[dict], *, chapter: str = "") -> str:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    city = _normalise_text(chapter) or _normalise_text(get_primary_city(row_list))
    row_types = {get_row_type(row) for row in row_list}
    text = _rows_text(row_list)

    if "Departure" in row_types and city:
        return f"Departure from {city}"
    if city and (_contains(text, "northern light village", "panorama suite")):
        return "Northern Lights village stay"
    if city:
        return welcome_arc_phrase(city)
    if is_scenic_route_text(text) or row_types.intersection({"Train", "Transport", "Cruise", "Ferry"}):
        return "Scenic route day"
    return "Arrival and time to settle in"


def choose_journey_arc_phrase(candidates: Sequence[str], *, chapter: str = "") -> str:
    """Pick a compact, cleaned Journey Arc phrase from ordered candidates."""

    cleaned: list[str] = []
    for phrase in candidates:
        value = sanitize_journey_arc_phrase(phrase, chapter=chapter)
        if value and value not in cleaned:
            cleaned.append(value)
    if not cleaned:
        cleaned = [welcome_arc_phrase(chapter)]
    for phrase in cleaned:
        if len(phrase) <= 48:
            return phrase[:1].upper() + phrase[1:]
    phrase = cleaned[0]
    lower = phrase.lower()
    if "northern lights" in lower and ("sámi" in lower or "sami" in lower):
        return "Northern Lights and Sámi culture"
    if "santa village" in lower and "northern lights" in lower:
        return "Northern Lights and Santa Village"
    words = phrase.split()
    shortened = ""
    for word in words:
        candidate = f"{shortened} {word}".strip()
        if len(candidate) > 48:
            break
        shortened = candidate
    return (shortened or phrase[:48].rstrip(" ,"))[:1].upper() + (shortened or phrase[:48].rstrip(" ,"))[1:]
