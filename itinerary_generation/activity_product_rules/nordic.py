"""Nordic/Arctic activity product matching."""

from __future__ import annotations

import re
from typing import Any

from text_polish import polish_title

from itinerary_generation.activity_product_core import ActivityProductFingerprint, match_product
from itinerary_generation.activity_product_text import canonicalize_activity_text


def _northern_lights_title(source_lower: str, source_title: str) -> str:
    cleaned_source_title = polish_title(canonicalize_activity_text(source_title)).strip(" -:|")
    if re.search(r"aurora\s+basecamp|aurora\s+base\s+camp", str(source_title or ""), flags=re.IGNORECASE):
        cleaned_source_title = re.sub(r"Northern Lights Basecamp", "Aurora Basecamp", cleaned_source_title, flags=re.IGNORECASE)
        cleaned_source_title = re.sub(r"Northern Lights Base Camp", "Aurora Basecamp", cleaned_source_title, flags=re.IGNORECASE)
        if "safari" in cleaned_source_title.lower():
            return "Northern Lights Safari to Aurora Basecamp"
    title_lower = cleaned_source_title.lower()
    if "safari" in title_lower and "northern lights basecamp" in title_lower:
        return "Northern Lights Safari to Aurora Basecamp"
    if "reindeer" in source_lower and any(marker in source_lower for marker in ("hunt", "hunting", "chase")):
        return "Northern Lights Hunt by Reindeer"
    if (
        cleaned_source_title
        and "northern lights" in title_lower
        and len(cleaned_source_title) <= 95
        and any(
            marker in title_lower
            for marker in (
                "minibus", "coach", "basecamp", "base camp", "safari",
                "photo", "photography", "free photos", "pro photos",
                "unlimited mileage", "cruise", "silent electric",
                "ice floating", "dinner", "snowmobile",
                "aurora base",
            )
        )
    ):
        return cleaned_source_title
    if "basecamp" in source_lower or "base camp" in source_lower:
        return "Northern Lights Safari to Aurora Basecamp"
    if "cruise" in source_lower or "silent electric ship" in source_lower:
        return "Northern Lights Cruise"
    if "floating" in source_lower or "float" in source_lower:
        return "Northern Lights Ice Floating"
    if "chase" in source_lower:
        return "Northern Lights Chase"
    if "photo tour" in source_lower or "photography" in source_lower:
        return "Northern Lights Photography Tour"
    if "dinner" in source_lower:
        return "Northern Lights Dinner"
    if "hunt" in source_lower or "mileage" in source_lower:
        return "Northern Lights Hunt"
    return "Northern Lights Experience"


def _ticket_title(source_title: str, fallback: str) -> str:
    if source_title and len(source_title) <= 80:
        lower = source_title.lower()
        if any(marker in lower for marker in ("ticket", "tickets", "admission", "entrance", "museum", "tivoli", "skyview", "munch", "vasa")):
            return source_title
    return fallback


def _icebreaker_match(source_lower: str, source_title: str) -> ActivityProductFingerprint:
    title_lower = source_title.lower()
    if "polar explorer" in source_lower or "polar explorer" in title_lower:
        return match_product(
            "polar_explorer_icebreaker_cruise",
            "icebreaker_cruise",
            "Polar Explorer Icebreaker Cruise",
            source_title=source_title,
            variant_tags=("polar_explorer",),
        )
    if "arctic explorer" in source_lower or "arctic explorer" in title_lower:
        display = source_title if source_title and "arctic explorer" in title_lower and len(source_title) <= 90 else "Arctic Explorer Icebreaker Cruise"
        return match_product(
            "arctic_explorer_icebreaker_cruise",
            "icebreaker_cruise",
            display,
            source_title=source_title,
            variant_tags=("arctic_explorer",),
        )
    if "sampo" in source_lower or "sampo" in title_lower:
        return match_product("sampo_icebreaker_cruise", "icebreaker_cruise", "Sampo Icebreaker Cruise", source_title=source_title, variant_tags=("sampo",))
    if "arktis" in source_lower or "arktis" in title_lower:
        return match_product("arktis_icebreaker_cruise", "icebreaker_cruise", "Arktis Icebreaker Cruise", source_title=source_title, variant_tags=("arktis",))
    return match_product(
        "icebreaker_cruise",
        "icebreaker_cruise",
        source_title if source_title and "icebreaker" in source_title.lower() and len(source_title) <= 90 else "Icebreaker Cruise",
        source_title=source_title,
        confidence="weak",
        warnings=("Review exact icebreaker product name.",),
    )


def _snowmobile_product_evidence(source_lower: str, source_title: str) -> bool:
    title_lower = source_title.lower()
    if "snowmobile" in title_lower:
        return True
    strong_patterns = (
        r"\bsnowmobile\s+(?:evening\s+)?safari\b",
        r"\bsnowmobile\s+adventure\b",
        r"\bsnowmobile\s+journey\b",
        r"\bsnowmobiling\b",
        r"\bdrive\s+a\s+snowmobile\b",
        r"\bsnowmobiles?\s+\(?(?:2\s+persons|shared)",
    )
    return any(re.search(pattern, source_lower, flags=re.IGNORECASE) for pattern in strong_patterns)


def _northern_lights_product_evidence(source_lower: str, source_title: str) -> bool:
    title_lower = source_title.lower()
    if "northern light" in title_lower or "aurora" in title_lower:
        return True
    return any(marker in source_lower for marker in (
        "northern lights hunt by minibus",
        "northern lights hunt",
        "northern lights safari",
        "northern lights chase",
        "northern lights basecamp",
        "northern lights dinner",
        "photo chase",
        "photo tour",
        "photography",
        "ice floating",
        "under the northern lights",
        "northern lights cruise",
    ))


def match_nordic_activity(
    row: dict[str, Any] | None,
    source: str,
    source_lower: str,
    source_title: str,
) -> ActivityProductFingerprint | None:
    """Match Lapland, Tromsø, Tallinn, Oslo and other Nordic activity families."""

    if "tallinn" in source_lower and "old town" in source_lower and "guided" in source_lower and not any(marker in source_lower for marker in ("ferry", "cruise duration", "round trip", "excursion to tallinn")):
        return match_product("tallinn_old_town_guided_tour", "walking_tour", "Old Town Guided Tour", source_title=source_title)

    if "tallinn" in source_lower and ("ferry" in source_lower or "cruise duration" in source_lower or "excursion to tallinn" in source_lower):
        tags = []
        if re.search(r"\bself[-\s]*guided\b|\bfree time\b|\bself explored\b", source_lower):
            tags.append("self_guided")
        elif re.search(r"\bguided\b[^.]{0,80}\bold town\b|\bold town\b[^.]{0,80}\bguided\b", source_lower):
            tags.append("guided_old_town")
        else:
            tags.append("ferry_framework")
        return match_product("day_excursion_to_tallinn", "ferry_excursion", "Day Excursion to Tallinn", source_title=source_title, variant_tags=tuple(tags))

    if "oslo" in source_lower and ("fjord cruise" in source_lower or "fjord sightseeing cruise" in source_lower or "oslo fjord" in source_lower or "oslofjord" in source_lower) and any(marker in source_lower for marker in ("electric", "silent", "sightseeing", "islands", "ship", "boat")):
        tags = []
        if "bygd" in source_lower:
            tags.append("bygdoy_stop")
        if "audio guide" in source_lower or "voice of norway" in source_lower:
            tags.append("audio_guide")
        if "island" in source_lower:
            tags.append("islands")
        if "100% electric" in source_lower or "electric" in source_lower:
            tags.append("electric_boat")
        title = source_title if source_title and "fjord" in source_title.lower() and "cruise" in source_title.lower() else ("Oslofjord Sightseeing Cruise" if "sightseeing" in source_lower else "Oslofjord Cruise with Silent Electric Ship")
        return match_product("oslofjord_cruise", "fjord_cruise", title, source_title=source_title, variant_tags=tuple(tags))

    if "oslo" in source_lower and ("munch museum" in source_lower or re.search(r"\bmunch\b", source_lower)) and any(marker in source_lower for marker in ("ticket", "tickets", "entrance", "entry", "admission", "museum")):
        return match_product("munch_museum_ticket", "admission", "Munch Museum Visit", source_title=source_title)

    if "santa claus" in source_lower and "husky" in source_lower and "reindeer" in source_lower:
        title = "City Highlights, Santa Claus Village & Husky-Reindeer Safari" if "city highlights" in source_lower else "Santa Claus Village, Husky & Reindeer Experience"
        tags = tuple(tag for tag, marker in (("arktikum", "arktikum"), ("lunch", "lunch")) if marker in source_lower)
        return match_product("santa_husky_reindeer", "combined_activity", title, source_title=source_title, variant_tags=tags)

    if "santa claus" in source_lower and "friends" in source_lower:
        return match_product("santa_claus_friends", "family_activity", "Meet Santa Claus and his friends", source_title=source_title)

    if "santa claus" in source_lower and "reindeer" in source_lower:
        if "snowmobile" in source_lower or "snowmobiles" in source_lower:
            return match_product("santa_snowmobile_reindeer", "snowmobile", "Santa Claus Village by Snowmobile & Reindeer Sleigh", source_title=source_title)
        if "husky" in source_lower or "huskies" in source_lower:
            return match_product("meet_santa_reindeer_huskies", "combined_activity", "Meet Santa Claus, Reindeer Ride & Greet Huskies", source_title=source_title)
        return match_product("santa_village_reindeer", "combined_activity", "Santa Claus Village & Reindeer Visit", source_title=source_title)

    if "korouoma" in source_lower:
        title = "Korouoma Frozen Waterfalls Hike & BBQ" if "frozen" in source_lower or "bbq" in source_lower else "Arctic Korouoma Canyon Wilderness Hike"
        return match_product("korouoma_canyon", "hike", title, source_title=source_title)

    if "ranua" in source_lower and "wildlife" in source_lower:
        return match_product("ranua_wildlife_park", "wildlife_park", "Arctic Wildlife Adventure to Ranua Park", source_title=source_title)

    if "icebreaker" in source_lower:
        return _icebreaker_match(source_lower, source_title)

    if "crystal lavvo" in source_lower or ("lyngen" in source_lower and "lavvo" in source_lower):
        return match_product("lyngen_crystal_lavvo", "overnight_activity", "Lyngen Alps Crystal Lavvo Stay", source_title=source_title)

    if "northern light" in source_lower or "aurora" in source_lower:
        if _northern_lights_product_evidence(source_lower, source_title) and not _snowmobile_product_evidence(source_lower, source_title):
            return match_product("northern_lights_activity", "northern_lights", _northern_lights_title(source_lower, source_title), source_title=source_title)

    if "snowmobile" in source_lower and _snowmobile_product_evidence(source_lower, source_title):
        if "evening" in source_lower or "aurora" in source_lower or "northern light" in source_lower:
            return match_product("snowmobile_evening_safari", "snowmobile", "Snowmobile Evening Safari & Aurora Opportunity", source_title=source_title)
        return match_product("snowmobile_adventure", "snowmobile", source_title if source_title and "snowmobile" in source_title.lower() else "Snowmobile Adventure", source_title=source_title)

    if "kvaløya" in source_lower or "sommarøy" in source_lower or "sommaroy" in source_lower:
        if "accessible" in source_lower:
            title = "Accessible Fjord Tour of Kvaløya & Sommarøy"
        elif "photo" in source_lower:
            title = "Photo Tour to Arctic Landscapes and Fjords"
        else:
            title = "Fjord Tour of Kvaløya & Sommarøy"
        return match_product("tromso_kvaloya_sommaroy_fjord", "fjord_sightseeing", title, source_title=source_title)

    if ("tromsø" in source_lower or "tromso" in source_lower) and any(marker in source_lower for marker in ("cable car", "round trip ticket", "viewpoint ticket", "fjellheisen")):
        return match_product("tromso_cable_car_ticket", "ticket", "Tromsø Cable Car Round-Trip Ticket", source_title=source_title)

    if "reindeer" in source_lower and "sami" in source_lower:
        if "night" in source_lower or "northern light" in source_lower:
            title = "Night Reindeer Sledding & Chance of Northern Lights"
        elif "sledding" in source_lower:
            title = "Short Reindeer Sledding, Reindeer Feeding & Sámi Culture"
        else:
            title = "Reindeer Feeding and Sámi Culture"
        return match_product("tromso_reindeer_sami", "sami_reindeer", title, source_title=source_title)

    if "wildlife photography" in source_lower and "longyearbyen" in source_lower:
        return match_product("svalbard_wildlife_photography", "wildlife_photography", "Wildlife Photography Around Longyearbyen", source_title=source_title)

    if "wildlife and glacier" in source_lower or "hybrid catamaran" in source_lower:
        return match_product("svalbard_wildlife_glacier_catamaran", "wildlife_cruise", "Wildlife & Glacier Hybrid Catamaran Tour", source_title=source_title)

    if "photo tour" in source_lower and "reine" in source_lower and "svolvær" in source_lower:
        return match_product("lofoten_photo_tour", "photo_tour", "Photo Tour to Reine, Vestvågøy, Flakstadøy & More", source_title=source_title)

    if "mountain hike" in source_lower and "abisko" in source_lower:
        return match_product("abisko_mountain_hike", "hike", "Mountain Hike in Abisko", source_title=source_title)

    return None
