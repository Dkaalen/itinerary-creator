"""Template builders for composed activity descriptions."""

from __future__ import annotations

import re

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text

from itinerary_generation.description_facts import (
    _extract_inclusion_facts,
    _extract_landmarks,
    _focus_from_title,
    _join,
)
from itinerary_generation.description_sources import _row_source
from itinerary_generation.tallinn import is_tallinn_ferry_framework, is_tallinn_old_town_guided_tour


def _compose_group_day(row: dict, source: str, title: str, city: str) -> str:
    places = _extract_landmarks(source, limit=8)
    focus = _focus_from_title(title)
    region = canonicalize_place_name(row.get("city", "")) or city or "the region"
    full = f"{title} {source}".lower()

    if "whale" in full and "hauganes" in full:
        return polish_client_text(
            "Today your guided group tour travels to Hauganes for the included Whale Watching experience. "
            "After time on the water looking for marine life, the route continues back to Reykjavík for the end of the guided programme."
        )

    if places:
        place_list = _join(places, max_items=6)
        if "golden circle" in full:
            return polish_client_text(f"Begin the guided route with the Golden Circle, including {place_list}, before continuing to the first overnight stop outside Reykjavík.")
        if "south coast" in full or "katla" in full:
            return polish_client_text(f"Follow the South Coast through {place_list}, combining waterfall scenery, black-sand coastline and the day’s included ice-cave experience where listed.")
        if "jökuls" in full or "jokuls" in full or "diamond beach" in full or "skaftafell" in full:
            return polish_client_text(f"Spend the day among Iceland’s glacier landscapes, with {place_list} included along the route towards the next overnight area.")
        if "eastfjord" in full or "egils" in full:
            return polish_client_text(f"Travel through the Eastfjords, where {place_list} give the day a quieter, more local feel before the overnight stop.")
        if "north iceland" in full or "mývatn" in full or "myvatn" in full or "dettifoss" in full:
            return polish_client_text(f"Cross into North Iceland with stops around {place_list}, linking waterfalls, geothermal areas and northern landscapes in one guided day.")
        return polish_client_text(f"Travel through {region} with your guide, with {place_list} shaping the day’s main stops before the overnight arrangements.")
    return polish_client_text(
        f"Travel with your guide through {region}, with the day focused on {focus} before continuing to your overnight stay."
    )


def _compose_known_activity(row: dict, source: str, title: str, city: str) -> str:
    landmark_source = " ".join([
        source,
        " ".join(row.get("includes", []) or []),
        " ".join(row.get("notable_sights", []) or []),
    ])
    full = f"{title} {landmark_source}".lower()
    places = _extract_landmarks(landmark_source, limit=6)
    inclusions = _extract_inclusion_facts(row, limit=4)
    city_phrase = f" in {city}" if city and city.lower() not in title.lower() else ""

    if is_tallinn_old_town_guided_tour(row):
        return "Explore Tallinn’s Old Town with a guide during your time ashore, with key landmarks and local context introduced along the walking route."
    if is_tallinn_ferry_framework(row):
        return "Travel between Helsinki and Tallinn by ferry, with the crossings forming the logistics for your time in Tallinn."
    if "food" in full and "culture" in full and "bergen" in full:
        return "Explore Bergen through local food and cultural stories, with tasting stops arranged along a guided route through the city."
    if ("whale watching" in full or "whale watching from downtown" in full) and (
        "arctic wildlife" in full or "rib boat" in full or "wildlife safari" in full or "alta" in full
    ):
        return polish_client_text(
            "Set out on Arctic waters for a whale watching and wildlife safari, with the RIB boat route shaped around fjord conditions, marine life and the surrounding northern landscapes."
        )
    if "whale watching" in full or "whale watching from downtown" in full:
        return "Set out from Reykjavík’s harbour for a whale watching experience, with onboard viewing areas and guidance while you look for marine life along the Icelandic coast."

    if "crystal lavvo" in full or ("lyngen" in full and "lavvo" in full):
        return polish_client_text(
            "Travel from Tromsø towards the Lyngen Alps for an overnight Crystal Lavvo experience, "
            "with meals, snowshoeing, Northern Lights guidance and return transfers arranged as part of the programme."
        )

    if ("northern lights" in full or "aurora" in full) and ("cruise" in full or "silent electric ship" in full or "boat" in full):
        return polish_client_text(f"Set out on an evening Northern Lights cruise{city_phrase}, with time on the water, simple refreshments where included and the Arctic night sky as the focus of the experience.")

    if "food tour" in full or "secret food" in full or "smørrebrød" in full or "smorrebrod" in full:
        if "copenhagen" in full or "smørrebrød" in full or "smorrebrod" in full or "danish meatballs" in full:
            return polish_client_text(f"Enjoy a guided food tour{city_phrase}, tasting local favourites such as smørrebrød, Danish meatballs and sweet bakery specialities while getting a flavour of the city’s food culture.")
        if "oslo" in full or city.lower() == "oslo":
            return "Explore Oslo through its food culture, with a guided route linking local flavours, hidden neighbourhood gems and stories from the city along the way."
        if "bergen" in full or city.lower() == "bergen":
            return "Explore Bergen through local food and cultural stories, with tasting stops arranged along a guided route through the city."
        return polish_client_text(f"Enjoy a guided food tour{city_phrase}, with tasting stops and local context arranged as part of the experience.")
    if "grand day trip" in full and "copenhagen" in full:
        return "Spend the day outside central Copenhagen with a guided route to Kronborg Castle, Frederiksborg Palace, Roskilde Cathedral and the Viking Ship Museum. The experience combines royal history, cultural landmarks and comfortable arranged transport."
    if "silfra" in full and ("snork" in full or "drysuit" in full):
        return "Experience the clear glacial water of Silfra on a guided drysuit snorkelling tour, with the required equipment and park arrangements included for the excursion."
    if "atv" in full or "quad" in full:
        return "Set out on a guided ATV adventure, with equipment provided and the route arranged around the surrounding black-sand and coastal landscapes."
    if "munch" in full and "museum" in full:
        return "Visit the Munch Museum at your own pace, with pre-arranged admission giving you time to explore the galleries and exhibitions independently."
    if "fløibanen" in full or "floibanen" in full:
        return "Use your round-trip Fløibanen ticket for a flexible visit to Mount Fløyen, with time to enjoy the viewpoint above Bergen during the day."
    if "fjellheisen" in full or ("round trip ticket" in full and "trom" in full):
        return "Use your round-trip Fjellheisen ticket for a flexible visit above Tromsø, with time to enjoy the panoramic views over the city, fjords and surrounding mountains."
    if (
        ("cable car" in full or "funicular" in full or "gondola" in full)
        and ("ticket" in full or "admission" in full)
        and ("view" in full or "mountain" in full or "viewpoint" in full)
    ):
        return polish_client_text(
            f"Use your pre-arranged ticket for a flexible visit by cable car{city_phrase}, "
            "with time to enjoy the mountain viewpoint and surrounding views during the day."
        )
    if "blue lagoon" in full and "volcano" in full:
        return "Begin with a guided visit to the Fagradalsfjall volcano area before ending the day in the warm geothermal waters of the Blue Lagoon. The experience balances dramatic volcanic scenery with time to relax."
    if "lava show" in full:
        return "Experience Icelandic volcanism up close during the Lava Show, where real molten lava is presented in a safe indoor setting with expert commentary."
    if "walking tour" in full or "citywalk" in full or "on foot" in full:
        safe_places = [place for place in places if not (place == "Tallinn Old Town" and "tallinn" not in full)]
        if "stockholm" in full and "old town" in full and "Stockholm Old Town" not in safe_places:
            safe_places.insert(0, "Stockholm Old Town")
        if safe_places:
            return polish_client_text(f"Set out on a guided walking tour{city_phrase}, with the route introducing {_join(safe_places, max_items=4)} alongside local stories and practical tips.")
        return polish_client_text(f"Set out on a guided walking tour{city_phrase}, with local stories, landmarks and practical tips introduced at an easy pace.")
    if "abisko" in full or "mountain hike" in full:
        return "Travel into the Abisko mountain landscape for a guided hike, with wide views, local nature stories and an included food stop along the route."
    if "korouoma" in full:
        return "Follow a guided hike through Korouoma Canyon, where frozen waterfalls, winter forest scenery and a warm outdoor food stop shape the experience."

    # High-confidence activity identities must beat incidental keywords.
    # For example, a fjord photo tour may mention that reindeer sometimes
    # wander through the area, but that should not turn the description into
    # a reindeer-feeding experience.
    if (
        "photo tour" in full
        or "photo excursion" in full
        or "arctic landscapes" in full
        or "scenic fjord safari" in full
        or "camera settings" in full
        or "nature photos" in full
        or "sommaroy" in full
        or "sommarøy" in full
    ) and ("fjord" in full or "landscape" in full or "scenic" in full):
        base = f"Travel outside {city} on a guided photo-focused excursion" if city else "Travel on a guided photo-focused excursion"
        return polish_client_text(
            f"{base} through Arctic landscapes, fjords and coastal scenery, "
            "with stops shaped around the weather, light and viewpoints of the day."
        )

    if "ice floating" in full or ("floating" in full and ("thermal" in full or "wetsuit" in full or "frozen lake" in full)):
        return polish_client_text(
            f"Float in a frozen lake{city_phrase} wearing a thermal survival suit, with warm drinks and cookies included "
            "and the Arctic night sky forming the focus of the experience."
        )

    if "santa claus" in full and "friends" in full:
        return "Experience a festive family-friendly visit with Santa Claus, reindeer and elves, including seasonal activities, warm refreshments and time for a private Santa meeting where included."
    if "husky" in full and "reindeer" in full:
        return polish_client_text(f"Spend the day around Arctic animal experiences{city_phrase}, combining husky and reindeer encounters with time at Santa Claus Village where included.")
    if "husky" in full:
        return polish_client_text(f"Meet the huskies{city_phrase} and enjoy an active Arctic experience arranged around the season and local conditions.")
    if "reindeer" in full:
        return polish_client_text(f"Meet and feed reindeer{city_phrase}, with time to learn more about this classic Lapland experience at an easy pace.")
    if "northern lights" in full or "aurora" in full:
        return polish_client_text(f"Head out in search of the Northern Lights{city_phrase}, with the route adapted to the evening conditions and local guidance included.")
    if "tallinn" in full:
        if is_tallinn_old_town_guided_tour(row):
            return "Explore Tallinn’s Old Town with a guide during your time ashore, with key landmarks and local context introduced along the walking route."
        return "Travel between Helsinki and Tallinn by ferry, with time arranged for your visit to Tallinn before returning to Helsinki."
    if "icebreaker" in full:
        return "Experience the Polar Explorer Icebreaker in Lapland, with the day centred on the frozen sea, Arctic scenery and the included icebreaker activities."
    if "husky" in full and "reindeer" in full:
        return polish_client_text(f"Spend the day around Arctic animal experiences{city_phrase}, combining husky and reindeer encounters with time at Santa Claus Village where included.")
    if "korouoma" in full:
        return "Follow a guided hike through Korouoma Canyon, where frozen waterfalls, winter forest scenery and a warm outdoor food stop shape the experience."
    if "abisko" in full or "mountain hike" in full:
        return "Travel into the Abisko mountain landscape for a guided hike, with wide views, local nature stories and an included food stop along the route."
    if "hike" in full or "hiking" in full or "nordmarka" in full:
        if "oslofjord" in full or "oslo fjord" in full or "nordmarka" in full:
            return "Follow a guided nature hike through the Nordmarka forest area, with local insight and viewpoints towards the Oslofjord forming the focus of the experience."
        return polish_client_text(f"Enjoy a guided hike{city_phrase}, with the route focused on local nature, scenery and a comfortable outdoor pace.")
    if "fjord" in full or "mostraumen" in full or "cruise" in full:
        if places:
            return polish_client_text(f"Enjoy a scenic water-based experience{city_phrase}, with the route focused on {_join(places, max_items=4)} and the surrounding landscapes.")
        return polish_client_text(f"Enjoy a scenic water-based experience{city_phrase}, adding a different perspective to the day’s route and landscapes.")
    if places:
        return polish_client_text(f"Enjoy {title}{city_phrase}, with the experience centred around {_join(places, max_items=5)}. The arrangements are prepared in advance so the day stays clear and easy to follow.")
    if inclusions:
        return polish_client_text(f"Enjoy {title}{city_phrase}, with the practical arrangements handled in advance and the included elements supporting a smooth experience.")
    return ""


def _fallback_description(row: dict, title: str, city: str) -> str:
    city_phrase = f" in {city}" if city and city.lower() not in title.lower() else ""
    lower = f"{title} {_row_source(row)}".lower()
    if "train" in lower or "rail" in lower:
        return polish_client_text(f"Continue by rail towards {city or 'your next destination'}, with the route and timing arranged as part of the day.")
    if "transfer" in lower or "self" in lower:
        return polish_client_text(f"Today’s travel arrangements{city_phrase} are kept clear and easy to follow, giving you a smooth transition to the next part of the journey.")
    return polish_client_text(f"Enjoy {title}{city_phrase}, with the schedule arranged to keep the experience clear, comfortable and easy to follow.")


