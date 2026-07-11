"""Keyword fallback descriptions for known activity rows."""

from __future__ import annotations

from text_polish import polish_client_text

from itinerary_generation.description_facts import _join
from itinerary_generation.activity_location_contract import activity_location_facts


def _photo_focused_description(full: str, city: str) -> str:
    if not any(
        marker in full
        for marker in [
            "photo tour",
            "photo excursion",
            "scenic fjord safari",
            "camera settings",
            "nature photos",
            "sommaroy",
            "sommarøy",
        ]
    ):
        return ""
    if not any(marker in full for marker in ["fjord", "landscape", "scenic"]):
        return ""
    base = f"Travel outside {city} on a guided photo-focused excursion" if city else "Travel on a guided photo-focused excursion"
    return polish_client_text(
        f"{base} through Arctic landscapes, fjords and coastal scenery, "
        "with stops shaped around the weather, light and viewpoints of the day."
    )


def _animal_and_aurora_description(full: str, city: str, city_phrase: str) -> str:
    if "husky" in full and "reindeer" in full:
        return polish_client_text(
            f"Spend the day around Arctic animal experiences{city_phrase}, combining husky and reindeer encounters with time at Santa Claus Village where included."
        )
    if "husky" in full:
        return polish_client_text(f"Meet the huskies{city_phrase} and enjoy an active Arctic experience arranged around the season and local conditions.")
    if "reindeer" in full:
        if "tromsø" in full or "tromso" in full or city.lower() in {"tromsø", "tromso"}:
            return polish_client_text(f"Meet and feed reindeer{city_phrase}, with time to learn about Sámi culture and Arctic traditions.")
        return polish_client_text(f"Meet and feed reindeer{city_phrase}, with time to learn more about this classic Arctic experience at an easy pace.")
    if ("northern lights" in full or "aurora" in full) and any(
        marker in full for marker in ["bbq", "barbecue", "campfire", "lappish"]
    ):
        return polish_client_text(
            f"Head outside the city in search of the Northern Lights{city_phrase}, with a campfire barbecue and local guidance included while you wait for clear skies."
        )
    if "northern lights" in full or "aurora" in full:
        return polish_client_text(f"Head out in search of the Northern Lights{city_phrase}, with the route adapted to the evening conditions and local guidance included.")
    return ""


def _outdoor_and_water_description(full: str, city_phrase: str, places: list[str]) -> str:
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
    return ""


def _city_and_water_description(full: str, city: str, location_facts) -> str:
    if any(marker in full for marker in ["oslofjord", "oslo fjord"]) and any(
        marker in full for marker in ["sightseeing cruise", "electric boat", "fjord sightseeing"]
    ):
        return polish_client_text(
            "Cruise through the Oslofjord by electric boat, with coastal scenery, islands and city landmarks forming the focus of the experience."
        )
    if "must-see bergen" in full or ("foot and boat" in full and "bergen" in full):
        return polish_client_text(
            "Explore Bergen from two perspectives: first on foot through the historic city streets and then by boat during the included harbour ride."
        )
    if "food" in full and "culture" in full and "bergen" in full:
        return "Explore Bergen through local food and cultural stories, with tasting stops arranged along a guided route through the city."
    if ("whale watching" in full or "whale watching from downtown" in full) and any(
        marker in full for marker in ["arctic wildlife", "rib boat", "wildlife safari", "alta"]
    ):
        return polish_client_text(
            "Set out on Arctic waters for a whale watching and wildlife safari, with the RIB boat route shaped around fjord conditions, marine life and the surrounding northern landscapes."
        )
    if "whale watching" in full or "whale watching from downtown" in full:
        base_city = location_facts.base_city or city
        if base_city:
            return polish_client_text(
                f"Set out from {base_city} for a whale watching experience, with onboard viewing areas and guidance while you look for marine life along the surrounding coast."
            )
        return "Set out on a whale watching experience, with onboard viewing areas and guidance while you look for marine life along the surrounding coast."
    if "crystal lavvo" in full or ("lyngen" in full and "lavvo" in full):
        return polish_client_text(
            "Travel from Tromsø towards the Lyngen Alps for an overnight Crystal Lavvo experience, "
            "with meals, snowshoeing, Northern Lights guidance and return transfers arranged as part of the programme."
        )
    return ""


def _food_and_ticket_description(full: str, title: str, city: str, city_phrase: str) -> str:
    if "sauna" in full and any(marker in full for marker in ["lakeside", "finnish", "wooden"]):
        return polish_client_text(
            f"Enjoy a Finnish sauna experience{city_phrase}, with time to relax by the lakeside setting and warm drinks or cookies included where specified."
        )
    if ("northern lights" in full or "aurora" in full) and any(marker in full for marker in ["cruise", "silent electric ship", "boat"]):
        return polish_client_text(
            f"Set out on an evening Northern Lights cruise{city_phrase}, with time on the water, simple refreshments where included and the Arctic night sky as the focus of the experience."
        )
    if "food tour" in full or "secret food" in full or "smørrebrød" in full or "smorrebrod" in full:
        if "copenhagen" in full or "smørrebrød" in full or "smorrebrod" in full or "danish meatballs" in full:
            return polish_client_text(
                f"Enjoy a guided food tour{city_phrase}, tasting local favourites such as smørrebrød, Danish meatballs and sweet bakery specialities while getting a flavour of the city’s food culture."
            )
        if "oslo" in full or city.lower() == "oslo":
            return "Explore Oslo through its food culture, with a guided route linking local flavours, hidden neighbourhood gems and stories from the city along the way."
        if "bergen" in full or city.lower() == "bergen":
            return "Explore Bergen through local food and cultural stories, with tasting stops arranged along a guided route through the city."
        return polish_client_text(f"Enjoy a guided food tour{city_phrase}, with tasting stops and local context arranged as part of the experience.")
    if "santa claus village" in full and "visit" in title.lower() and not any(
        marker in title.lower() for marker in ["husky", "reindeer", "snowmobile"]
    ):
        return polish_client_text(
            "Visit Santa Claus Village, with time for Santa’s Post Office, the Arctic Circle crossing and self-guided exploration of the festive village surroundings."
        )
    if (
        any(marker in full for marker in ["cable car", "funicular", "gondola"])
        and any(marker in full for marker in ["ticket", "admission"])
        and any(marker in full for marker in ["view", "mountain", "viewpoint"])
    ):
        return polish_client_text(
            f"Use your pre-arranged ticket for a flexible visit by cable car{city_phrase}, "
            "with time to enjoy the mountain viewpoint and surrounding views during the day."
        )
    return ""


def _adventure_and_landmark_description(full: str, city_phrase: str, places: list[str]) -> str:
    if "grand day trip" in full and "copenhagen" in full:
        return "Spend the day outside central Copenhagen with a guided route to Kronborg Castle, Frederiksborg Palace, Roskilde Cathedral and the Viking Ship Museum. The experience combines royal history, cultural landmarks and comfortable arranged transport."
    if "silfra" in full and ("snork" in full or "drysuit" in full):
        return "Experience the clear glacial water of Silfra on a guided drysuit snorkelling tour, with the required equipment and park arrangements included for the excursion."
    if "atv" in full or "quad" in full:
        return "Set out on a guided ATV adventure, with equipment provided and the route arranged around the surrounding black-sand and coastal landscapes."
    if "fløibanen" in full or "floibanen" in full:
        return "Use your round-trip Fløibanen ticket for a flexible visit to Mount Fløyen, with time to enjoy the viewpoint above Bergen during the day."
    if "blue lagoon" in full and "volcano" in full:
        return "Begin with a guided visit to the Fagradalsfjall volcano area before ending the day in the warm geothermal waters of the Blue Lagoon. The experience balances dramatic volcanic scenery with time to relax."
    if "lava show" in full:
        return "Experience Icelandic volcanism up close during the Lava Show, where real molten lava is presented in a safe indoor setting with expert commentary."
    if "walking tour" in full or "citywalk" in full or "on foot" in full:
        safe_places = [place for place in places if not (place == "Tallinn Old Town" and "tallinn" not in full)]
        if "stockholm" in full and "old town" in full and "Stockholm Old Town" not in safe_places:
            safe_places.insert(0, "Stockholm Old Town")
        if safe_places:
            return polish_client_text(
                f"Set out on a guided walking tour{city_phrase}, with the route introducing {_join(safe_places, max_items=8)} alongside local stories and practical tips."
            )
        return polish_client_text(f"Set out on a guided walking tour{city_phrase}, with local stories, landmarks and practical tips introduced at an easy pace.")
    return ""


def _final_known_description(full: str, title: str, city_phrase: str, places: list[str], inclusions: list[str], location_facts) -> str:
    if "tallinn" in full:
        return "Travel between Helsinki and Tallinn by ferry, with time arranged for your visit to Tallinn before returning to Helsinki."
    if "icebreaker" in full:
        product_name = "Polar Explorer Icebreaker" if "polar explorer" in full else "Arctic Explorer Icebreaker" if "arctic explorer" in full else "Sampo Icebreaker" if "sampo" in full else "Arktis Icebreaker" if "arktis" in full else "icebreaker cruise"
        return f"Experience the {product_name} in Lapland, with the day centred on the frozen sea, Arctic scenery and the included icebreaker activities."
    if places:
        place_list = _join(places, max_items=5)
        if location_facts.excursion_region == "Blue Lagoon":
            return polish_client_text(
                f"Visit the Blue Lagoon from {location_facts.base_city or 'Reykjavík'}, with comfort admission, return transfers and time in the geothermal waters arranged as part of the day."
            )
        if location_facts.excursion_region == "Jökulsárlón Glacier Lagoon":
            return polish_client_text("Visit Jökulsárlón Glacier Lagoon for a scenery-led day, with the included boat tour adding time among the floating ice where conditions allow.")
        if location_facts.is_excursion and location_facts.base_city:
            region_name = location_facts.excursion_region
            if not region_name.startswith(("Iceland", "Snæfellsnes", "Jökulsárlón")):
                region_name = "the " + region_name
            return polish_client_text(
                f"Explore {region_name} from {location_facts.base_city}, with {place_list} shaping the main stops of the experience."
            )
        return polish_client_text(f"Enjoy {title}{city_phrase}, with the experience centred around {place_list}.")
    if inclusions:
        return polish_client_text(f"Enjoy {title}{city_phrase}, with the practical arrangements handled in advance and the included elements supporting a smooth experience.")
    return ""


def match_known_activity_description(
    *,
    row: dict,
    title: str,
    city: str,
    full: str,
    places: list[str],
    inclusions: list[str],
    city_phrase: str,
) -> str:
    """Return a keyword-based activity description, or ``""``."""

    location_facts = activity_location_facts(row, title=title, city=city, source_text=full)
    for matcher in [
        lambda: _city_and_water_description(full, city, location_facts),
        lambda: _food_and_ticket_description(full, title, city, city_phrase),
        lambda: _adventure_and_landmark_description(full, city_phrase, places),
        lambda: _photo_focused_description(full, city),
        lambda: _animal_and_aurora_description(full, city, city_phrase),
        lambda: _outdoor_and_water_description(full, city_phrase, places),
        lambda: _final_known_description(full, title, city_phrase, places, inclusions, location_facts),
    ]:
        description = matcher()
        if description:
            return description
    return ""
