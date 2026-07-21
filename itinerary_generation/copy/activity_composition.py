"""Service-specific deterministic activity and group-tour intro composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from itinerary_generation.activity_location_contract import activity_location_facts
from itinerary_generation.activity_mode_contract import resolve_activity_mode
from shared.text import clean_space


@dataclass(frozen=True)
class TextRule:
    """A marker-driven text decision with explicit match semantics."""

    markers: tuple[str, ...]
    template: Callable[[str, str], str]
    match_all: bool = False

    def matches(self, text: str) -> bool:
        if self.match_all:
            return all(marker in text for marker in self.markers)
        return any(marker in text for marker in self.markers)

    def render(self, title: str, city: str) -> str:
        return self.template(title, city)


def _normalise_text(value: object) -> str:
    return clean_space(value)


def _specific_iceland_intro(title: str, city: str, source_text: str) -> str:
    facts = activity_location_facts(title=title, city=city, source_text=source_text)
    lower = f"{title} {city} {source_text}".casefold()
    if "whale" in lower and "blue lagoon" in lower:
        return "Today combines whale watching from Reykjavík with time at the Blue Lagoon, keeping the day varied without blurring the two separate experiences."
    if facts.excursion_region == "Golden Circle":
        return "Follow the Golden Circle from Reykjavík today, with Þingvellir, Strokkur and Gullfoss shaping the main route."
    if facts.excursion_region == "Iceland’s South Coast":
        return "Head out from Reykjavík along Iceland’s South Coast, where waterfalls, glacier scenery and black-sand coastline shape the day."
    if facts.excursion_region == "Snæfellsnes Peninsula":
        return "Set out from Reykjavík for the Snæfellsnes Peninsula, with the day focused on coastal scenery, mountain views and small-town stops along the route."
    if facts.excursion_region == "Fagradalsfjall and Meradalir":
        return "Today focuses on the Fagradalsfjall and Meradalir volcanic landscape, with a guided hike arranged from Reykjavík."
    if facts.excursion_region == "Jökulsárlón Glacier Lagoon":
        return "Travel from Reykjavík to Jökulsárlón Glacier Lagoon for a long scenery-led day, with the boat tour included as part of the experience."
    if facts.excursion_region == "Blue Lagoon":
        return "Travel from Reykjavík to the Blue Lagoon for a flexible geothermal bathing experience, with return transfer and admission arranged."
    if facts.excursion_region == "Reykjavík harbour and coast":
        return "Set out from Reykjavík harbour for whale watching, with onboard guidance and coastal viewing areas included while you look for marine life."
    return ""


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
        lambda title, city: f"Walk through {city} with {title}, using local stories, historic streets and key landmarks to give the place more context.",
    ),
    TextRule(
        ("crystal lavvo", "lavvo stay", "glass igloo", "igloo stay"),
        lambda title, city: f"Travel from {city} for {title}, with the overnight setting, included activities and evening sky-watching forming one complete Arctic experience.",
    ),
    TextRule(
        ("northern lights", "aurora"),
        lambda title, city: "The day is kept easy around your evening Northern Lights experience, giving you time to settle before heading out with local guidance after dark.",
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
        match_all=True,
    ),
    TextRule(
        ("photo", "sommar", "landscape"),
        lambda title, city: f"Set out from {city} on {title}, with the route shaped around light, weather and the best viewpoints of the day.",
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
    iceland_intro = _specific_iceland_intro(title, city_text, source_text)
    if iceland_intro:
        return iceland_intro
    if "electric boat" in searchable and any(marker in searchable for marker in ("oslo", "oslofjord", "trollcruise")):
        return f"See Oslo from the fjord today, with {title} adding harbour views, island scenery and an easy perspective on the Norwegian capital."
    for rule in ACTIVITY_INTRO_RULES:
        if rule.matches(searchable):
            return rule.render(title, city_text)
    mode = resolve_activity_mode(title, source_text)
    if mode.water_led:
        return f"Sail from {city_text} on {title}, with the route and time on the water shaping the experience."
    if compact:
        return f"Today focuses on {title}, with the remaining schedule kept flexible around the included experience."
    return f"Today focuses on {title}, with timing, meeting details and inclusions kept clear for the experience."


def client_group_tour_intro(activity_title: str, city: str, source_text: str = "") -> str:
    """Return one shared intro for guided group-tour continuation days."""

    title = _normalise_text(activity_title) or "today's guided route"
    city_text = _normalise_text(city) or "the route"
    searchable = f"{title} {source_text}".lower()
    for rule in GROUP_TOUR_INTRO_RULES:
        if rule.matches(searchable):
            return rule.render(title, city_text)
    return f"The guided programme continues through {city_text} today, with the main stops, route and overnight arrangements handled as part of the tour."


__all__ = ["TextRule", "client_activity_intro", "client_group_tour_intro"]
