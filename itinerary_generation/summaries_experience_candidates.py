"""Ordered experience candidate prioritization."""
from __future__ import annotations

from itinerary_generation.destination_copy import destination_arc_fallback
from itinerary_generation.summaries_text import _has

def _add_iceland_candidates(candidates, signals):
    text = signals.text
    if _has(text, "borgarfjörður", "borgarfjordur", "hraunfossar", "barnafoss"):
        candidates.append("Borgarfjörður valley and waterfalls")
    if _has(text, "snæfellsnes", "snaefellsnes", "kirkjufell", "arnarstapi"):
        candidates.append("Snæfellsnes Peninsula highlights")
    if _has(text, "katla") and _has(text, "seljalandsfoss", "skógafoss", "skogafoss", "reynisfjara"):
        candidates.append("South Coast waterfalls and Katla Ice Cave")
    elif _has(text, "south coast waterfalls", "seljalandsfoss", "skógafoss", "skogafoss", "reynisfjara"):
        candidates.append("South Coast waterfalls and glacier hike")
    if _has(text, "skaftafell", "vatnajökull", "vatnajokull") and _has(text, "jökulsárlón", "jokulsarlon", "diamond beach"):
        candidates.append("Vatnajökull glacier and Jökulsárlón")
    elif _has(text, "jökulsárlón", "jokulsarlon", "diamond beach", "ice cave"):
        candidates.append("Glacier lagoon and ice caves")
    if _has(text, "eastfjords", "egilsstaðir", "egilsstadir", "hallormsstaðaskógar", "lagafljót"):
        candidates.append("Eastfjords and local life")
    if _has(text, "dettifoss", "mývatn", "myvatn", "goðafoss", "godafoss", "north iceland"):
        candidates.append("North Iceland waterfalls and Mývatn")
    if signals.has_whale and _has(text, "hauganes", "return to reykjavík", "return to reykjavik"):
        candidates.append("Whale watching and return to Reykjavík")


def _add_route_and_city_candidates(candidates, signals):
    text = signals.text
    if _has(text, "oslofjord", "oslo fjord"):
        candidates.append("Oslofjord cruise and capital welcome" if signals.has_arrival else "City sights and Oslofjord cruising")
    if signals.chapter_city.lower() == "kristiansand" and _has(text, "coastal cruise", "cruise to bergen", "southern norway", "southern coastal"):
        candidates.append("South Coast and coastal cruise")
    if _has(text, "otra river") or (signals.chapter_city.lower() == "kristiansand" and _has(text, "kayaking", "kayak")):
        candidates.append("Otra River kayaking and southern coast")
    elif _has(text, "nærøyfjord", "naeroyfjord") and _has(text, "kayaking", "kayak"):
        candidates.append("Nærøyfjord kayaking and onward travel")
    if _has(text, "lysefjord", "preikestolen", "pulpit rock"):
        candidates.append("Lysefjord and Preikestolen cruise")
    if _has(text, "guided walking tour of bergen", "bergen past & present") and signals.has_cable:
        candidates.append("Historic Bergen and Fløibanen views")
    if signals.has_nutshell and signals.has_food:
        candidates.append(f"{signals.nutshell_title} and Oslo food tour")
    if _has(text, "spend time at leisure onboard the cruise") and signals.row_types == {"Cruise"}:
        candidates.append("Coastal cruise at leisure")
    if _has(text, "cruise to bergen") and _has(text, "kirkenes"):
        candidates.append("Cruise departure towards Bergen")
    if _has(text, "cruise arrival to bergen", "arrival to bergen"):
        candidates.append("Cruise arrival and Bergen stay")
    if signals.has_tallinn:
        candidates.append("Tallinn Old Town day trip")
    if signals.has_nutshell:
        candidates.append(signals.nutshell_title)
    elif _has(text, "nærøyfjord", "naeroyfjord") and _has(text, "stegastein", "borgund"):
        candidates.append("Nærøyfjord, Stave Church and Stegastein")
    elif _has(text, "foot", "walking tour") and _has(text, "boat", "city cruise") and signals.chapter_city.lower() == "bergen":
        candidates.append("Scenic rail and Bergen by foot and boat")
    elif _has(text, "nærøyfjord", "naeroyfjord", "flåmsbanen", "flamsbanen", "flåm railway", "flam railway"):
        candidates.append("Scenic rail and fjord travel")
    elif _has(text, "scenic train", "train transfer", "rail") and signals.chapter_city:
        candidates.append(f"Scenic rail to {signals.chapter_city}")
    if signals.has_golden and signals.has_silfra:
        candidates.append("Golden Circle and Silfra snorkelling")
    elif signals.has_silfra:
        candidates.append("Silfra snorkelling")
    elif signals.has_golden:
        candidates.append("Golden Circle route")


def _add_theme_candidates(candidates, signals):
    text = signals.text
    if signals.has_lagoon and signals.has_self_drive and signals.has_whale:
        candidates.append("Lagoon, self-drive route and whale watching")
    elif signals.has_lagoon and signals.has_self_drive:
        candidates.append("Lagoon and scenic self-drive route")
    elif signals.has_lagoon:
        candidates.append("Blue Lagoon experience" if "blue lagoon" in text else "Sky Lagoon experience" if "sky lagoon" in text else "Lagoon and wellness")
    if signals.has_south and signals.has_adventure:
        candidates.append("South Coast scenery and soft adventure")
    elif signals.has_south:
        candidates.append("South Coast scenery")
    if signals.has_reindeer_sami and signals.has_aurora:
        if "santa claus village" in text:
            candidates.append("Northern Lights, Santa Village and Arctic experiences")
        elif signals.has_fjord or signals.has_nature:
            candidates.append("Sámi culture, fjords and northern lights")
        else:
            candidates.append("Northern Lights, Sámi culture and Arctic experiences")
    elif signals.has_reindeer_sami:
        candidates.append("Sámi culture and Arctic experiences")
    elif signals.has_aurora and signals.has_whale:
        candidates.append("Wildlife, Northern Lights and Arctic coast")
    elif signals.has_aurora:
        candidates.append("Northern Lights experiences")


def _add_fjord_and_experience_candidates(candidates, signals):
    text = signals.text
    chapter_city = signals.chapter_city
    if _has(text, "trollfjord"):
        candidates.append("Lofoten scenery and Trollfjord cruising")
    elif _has(text, "lofoten", "henningsvær", "haukland", "reine", "vestvågøy", "flakstadøy"):
        candidates.append("Lofoten scenery and photography")
    elif signals.has_fjord and signals.has_city and chapter_city.lower() == "oslo":
        candidates.append("City sights and Oslofjord cruising")
    elif signals.has_fjord and signals.has_cable:
        if _has(text, "bergen", "fløibanen", "floibanen") and not _has(text, "tromsø", "tromso", "alta", "svalbard", "kiruna"):
            candidates.append("City, fjord and funicular")
        elif _has(text, "arctic", "tromsø", "tromso", "alta", "svalbard", "kiruna"):
            candidates.append("Arctic fjords and viewpoints")
        else:
            candidates.append("Fjord views and funicular")
    elif signals.has_fjord and signals.has_whale:
        candidates.append("Coastal wildlife and fjord scenery")
    elif signals.has_fjord:
        if _has(text, "bergen") and not _has(text, "arctic", "tromsø", "tromso", "alta", "svalbard", "kiruna"):
            candidates.append("Bergen fjords and coastal cruising")
        else:
            candidates.append("Fjord scenery and coastal cruising")

    if signals.has_city and _has(text, "vasa"):
        candidates.append("Old Town, Vasa Museum and city discovery")
    elif signals.has_city and _has(text, "old town", "stockholm"):
        candidates.append("Old Town and city discovery")
    elif signals.has_city and signals.has_arrival:
        candidates.append("Arrival and guided city discovery")
    elif signals.has_city:
        candidates.append("Guided city discovery")
    if signals.has_food and not any("food" in c.lower() for c in candidates):
        candidates.append("Local food culture")
    if signals.has_nature and not any(marker in " ".join(candidates).lower() for marker in ["nature", "lofoten", "arctic fjords", "south coast"]):
        candidates.append("Scenic nature experiences")
    if signals.has_leisure and len(candidates) < 2:
        candidates.append(destination_arc_fallback(chapter_city))


def _add_fallback_candidates(candidates, signals):
    text = signals.text
    chapter_city = signals.chapter_city
    if not candidates and _has(text, "coach transfer", "bus 150", "long distance panorama coach") and signals.has_aurora:
        candidates.append("Coach journey and Northern Lights")
    if signals.has_departure and not candidates:
        candidates.append(f"Departure from {chapter_city}" if chapter_city else "Departure arrangements")
    if signals.has_arrival and not candidates:
        candidates.append(f"Welcome to {chapter_city}" if chapter_city else "Arrival and time to settle in")
    if signals.has_hotel_only:
        candidates.append(f"Welcome to {chapter_city}" if chapter_city else "Accommodation as listed")
    if signals.travel_only_with_hotel and not candidates:
        if signals.has_departure:
            candidates.append(f"Departure from {chapter_city}" if chapter_city else "Departure arrangements")
        elif chapter_city:
            candidates.append(f"Welcome to {chapter_city}")
        elif signals.row_types.intersection({"Train", "Transport", "Cruise", "Ferry"}):
            candidates.append("Scenic route day")
        else:
            candidates.append("Arrival and time to settle in")
    if not candidates:
        if signals.has_flight and chapter_city:
            candidates.append(f"Welcome to {chapter_city}")
        elif signals.row_types.intersection({"Train", "Transport", "Cruise", "Ferry"}):
            candidates.append("Scenic route day")
        else:
            candidates.append(destination_arc_fallback(chapter_city))


def _candidate_phrases(signals):
    candidates = []
    _add_iceland_candidates(candidates, signals)
    _add_route_and_city_candidates(candidates, signals)
    _add_theme_candidates(candidates, signals)
    _add_fjord_and_experience_candidates(candidates, signals)
    _add_fallback_candidates(candidates, signals)
    return candidates

