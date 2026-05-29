"""Intro text helpers for day planning."""

from __future__ import annotations

import re


def _group_tour_intro_from_source(title: str, source: str) -> str:
    lower = f"{title} {source}".lower()
    if "whale" in lower and "hauganes" in lower:
        return "Your guided group tour continues today to Hauganes for Whale Watching before returning to Reykjavík. The day is organised around the included boat experience and the final guided route back to the capital."
    return ""


def _intro_for_title(title: str, city: str, pattern: str) -> str:
    if pattern == "leisure_day":
        return f"Enjoy a slower day in {city}, with time to explore independently, relax, or add optional experiences that suit your interests." if city else "Enjoy a slower day, with time to explore independently or relax."
    if pattern == "multi_activity_day":
        return f"Today combines complementary experiences in {city}, with the schedule arranged so the day feels varied but easy to follow." if city else "Today combines complementary experiences, with the schedule arranged so the day feels varied but easy to follow."
    if pattern == "travel_day":
        dest = re.sub(r"^(?:Train|Flight|Cruise|Coach Transfer|Scenic Train Transfer|Panoramic Coach Transfer)\s+(?:from\s+.+?\s+)?to\s+", "", title, flags=re.I)
        return f"The journey continues towards {dest}, with the travel arrangements structured to keep the route clear, comfortable, and easy to follow." if dest and dest != title else "The journey continues today, with the travel arrangements structured to keep the route clear, comfortable, and easy to follow."
    if pattern == "self_drive_route_day":
        return f"Today’s self-drive route is arranged to keep the journey clear and scenic, with suggested stops and overnight plans laid out in a simple way."
    if pattern == "hop_on_city_day":
        return f"Use the day flexibly to explore {city} at your own pace, with sightseeing transport arranged to make the city’s main areas easy to reach." if city else "Use the day flexibly to explore at your own pace, with sightseeing transport arranged to make the main areas easy to reach."
    if pattern == "single_activity_day":
        return f"Today is centred on {title} in {city}, with the surrounding schedule kept clear and comfortable." if city and city.lower() not in title.lower() else f"Today is centred on {title}, with the surrounding schedule kept clear and comfortable."
    return ""
