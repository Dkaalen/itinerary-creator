"""Service-specific deterministic activity and group-tour intro composition."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable


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


ACTIVITY_INTRO_RULES: tuple[TextRule, ...] = (
    TextRule(
        ("lysefjord", "preikestolen", "pulpit rock"),
        lambda title, city: f"The day centres on Lysefjord, with {title} carrying you from Stavanger beneath steep mountain walls, waterfalls and the viewpoint of Preikestolen.",
    ),
    TextRule(
        ("oslofjord", "trollcruise"),
        lambda title, city: f"See Oslo from the fjord today, with {title} adding harbour views, island scenery and an easy perspective on the Norwegian capital.",
    ),
    TextRule(
        ("otra river",),
        lambda title, city: f"See Kristiansand from river level today, with {title} giving you time outdoors along the city’s waterways.",
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
        lambda title, city: f"Walk through {city} with {title}, using local stories, historic streets and lesser-known corners to give the place more context.",
    ),
    TextRule(
        ("northern lights", "aurora"),
        lambda title, city: "The day is kept easy around your evening Northern Lights experience, giving you time to settle before heading out with local guidance after dark.",
    ),
    TextRule(
        ("fjord", "cruise", "silent electric ship"),
        lambda title, city: f"Sail from {city} on {title}, with fjord scenery, coastal landmarks and time on the water shaping the day.",
    ),
    TextRule(
        ("funicular", "cable car", "fjellheisen", "fløibanen", "floibanen"),
        lambda title, city: f"Use today for a flexible viewpoint visit in {city}, with {title} arranged so you can choose the timing that suits the day.",
    ),
    TextRule(
        ("santa claus village", "santa's post office", "arctic circle"),
        lambda title, city: f"Visit Santa Claus Village from {city}, with transfer arrangements and self-guided time around Santa’s Post Office, the Arctic Circle crossing and the village surroundings.",
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


def client_activity_intro(activity_title: str, city: str, source_text: str = "", *, compact: bool = False) -> str:
    """Return one shared activity-day intro used by all day-intro paths."""

    title = _normalise_text(activity_title) or "the arranged experience"
    city_text = _normalise_text(city) or "the experience area"
    searchable = f"{title} {city_text} {source_text}".lower()
    if "electric boat" in searchable and any(marker in searchable for marker in ("oslo", "oslofjord", "trollcruise")):
        return f"See Oslo from the fjord today, with {title} adding harbour views, island scenery and an easy perspective on the Norwegian capital."
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
