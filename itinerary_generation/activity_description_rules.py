"""Deterministic activity-description fallback rules.

This module owns the broad keyword fallbacks used after real supplier prose,
product-rule matches, and the activity training catalogue have had first right
of refusal.  Keeping these rules outside the main helper prevents one large
function from mixing source extraction, catalogue priority, and generic copy.
"""

from __future__ import annotations


def detail_variant(default: str, *, detail_level: str, concise: str | None = None, rich: str | None = None) -> str:
    """Return copy for the active detail level without duplicating branches."""

    if detail_level == "Elegant concise" and concise:
        return concise
    if detail_level == "Rich descriptive" and rich:
        return rich
    return default


def specific_activity_description(*, title: str, city: str, detail_level: str) -> str:
    """Return product-specific fallback copy before catalogue lookups."""

    if "icebreaker" in title and "cruise" in title:
        return "Experience the Arctic coastline from an icebreaker cruise, with time on the frozen sea and the included floating experience arranged as part of the excursion."
    if "wildlife photography" in title and "longyearbyen" in title:
        return "Spend time looking for Arctic wildlife and landscape photo opportunities around Longyearbyen with the guidance arranged for the experience."
    if "mountain hike" in title and "abisko" in title:
        return "Hike in the Abisko mountain landscape, with time for views, local nature stories and the included food stop during the excursion."
    if "fjord" in title and ("minivan" in title or "vip" in title or "kvaløya" in title or "sommarøy" in title):
        return "Explore the coastal scenery around Tromsø by road, with fjords, mountains, beaches and Arctic landscapes forming the focus of the day."
    if "lofoten" in title and "trollfjord" in title:
        return detail_variant(
            "Travel through Lofoten by land and sea, with a scenic cruise into the dramatic Trollfjord.",
            detail_level=detail_level,
            concise="Travel through Lofoten by land and sea, including Trollfjord scenery.",
            rich="Experience Lofoten by land and sea, with a scenic cruise into the dramatic Trollfjord landscape.",
        )
    if "city walking" in title and "canal" in title and "copenhagen" in title:
        return detail_variant(
            "Explore central Copenhagen on foot with a local host, including key landmarks and a scenic canal experience.",
            detail_level=detail_level,
            concise="Explore Copenhagen on foot and by canal with a local host.",
            rich="Explore central Copenhagen with a local host, combining city landmarks, local stories, and a scenic canal experience.",
        )
    if "essential oslo" in title:
        return _oslo_walking_description(detail_level)
    if "guided walking tour" in title:
        if "copenhagen" in city or "copenhagen" in title:
            return detail_variant(
                "Explore central Copenhagen on foot with a local guide, with time for local stories and key city landmarks.",
                detail_level=detail_level,
                concise="Explore central Copenhagen on foot with a local guide.",
                rich="Explore central Copenhagen on foot with a local guide, with time for local stories, major landmarks, and the atmosphere of the city.",
            )
        if "oslo" in city or "oslo" in title:
            return _oslo_walking_description(detail_level)
    if "must-see bergen" in title or ("foot and boat" in title and "bergen" in title):
        return detail_variant(
            "Explore Bergen on foot and by boat, combining historic city streets with a scenic perspective from the water.",
            detail_level=detail_level,
            concise="Explore Bergen on foot and by boat.",
            rich="Explore Bergen from two perspectives: on foot through the historic city streets and by boat from the surrounding waters.",
        )
    if "hop on" in title or "hop-on" in title or "hop off" in title or "hop-off" in title:
        return detail_variant(
            "Use your flexible ticket to explore the city at your own pace.",
            detail_level=detail_level,
            rich="Use your flexible ticket to explore the city at your own pace, choosing the stops and sights that suit your day best.",
        )
    return ""


def keyword_activity_description(*, combined: str, destination_phrase: str) -> str:
    """Return broad keyword fallback copy after catalogue lookups."""

    if "blue lagoon" in combined or "sky lagoon" in combined or ("lagoon" in combined and ("admission" in combined or "spa" in combined or "ritual" in combined)):
        return "Enjoy this lagoon and wellness experience, with admission details arranged as part of the day."
    if "whale watching" in combined or "whale" in combined:
        return f"Join a whale watching experience{destination_phrase}, with time on the water and guidance from the local crew."
    if "snork" in combined or "silfra" in combined:
        return "Experience Silfra with the arranged equipment and local guidance, following the meeting details provided for the activity."
    if "atv" in combined or "quad" in combined:
        return "Head out on an ATV experience, with safety equipment and guidance provided for the route."
    if "glacier" in combined or "crampon" in combined:
        return "Join a guided glacier experience, with the required safety equipment provided before heading onto the ice."
    if "suomenlinna" in combined:
        return "A guided introduction to Helsinki’s city highlights combined with a visit to the historic sea fortress island of Suomenlinna."
    if ("reindeer feeding" in combined or "sámi" in combined or "sami" in combined) and not ("northern lights chase" in combined or "northern lights hunt" in combined or "aurora hunt" in combined):
        return "Meet the reindeer herd, learn about Sámi culture and enjoy a warm meal as part of the Arctic experience."
    if "northern lights basecamp" in combined:
        return "Spend the evening at a dedicated Northern Lights basecamp, with time to wait for the aurora in a comfortable Arctic setting."
    if "northern lights" in combined or "aurora" in combined:
        return _northern_lights_description(combined)
    if "ranua" in combined:
        return "Travel to Ranua Wildlife Park for a look at Arctic wildlife in a forested Lapland setting, with time to enjoy the experience at an easy pace."
    if "wildlife" in combined:
        return f"Enjoy a wildlife-focused experience{destination_phrase}, with the details arranged as part of the day."
    if "fjord tour" in combined or "kvaløya" in combined or "sommarøy" in combined:
        return "Explore the coastal scenery around Tromsø, with fjords, islands and Arctic landscapes forming the focus of the day."
    if "funicular" in combined or "fløibanen" in combined:
        return "Ride the Fløibanen funicular for an easy ascent above Bergen and views over the city, harbour and surrounding mountains."
    if "photo tour" in combined and ("fjord" in combined or "landscape" in combined):
        return f"Explore scenic fjords and Arctic landscapes{destination_phrase}, with guidance on viewpoints and photography along the way."
    if "walking" in combined or "guided" in combined:
        return f"Enjoy a guided experience{destination_phrase}, with local context and a clear route through the day’s main highlights."
    if "boat" in combined or "cruise" in combined or "canal" in combined:
        return f"See the area from the water, adding a scenic perspective to the day{destination_phrase}."
    return ""


def _oslo_walking_description(detail_level: str) -> str:
    return detail_variant(
        "Explore central Oslo on foot with a local guide, including key landmarks around the city center.",
        detail_level=detail_level,
        concise="Explore central Oslo on foot with a local guide.",
        rich="Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital.",
    )


def _northern_lights_description(combined: str) -> str:
    if "reindeer" in combined and ("hunt" in combined or "chase" in combined):
        return "Head into the winter landscape for a Northern Lights hunt by reindeer, with warm drinks and Arctic atmosphere included in the experience."
    if "bbq" in combined or "barbecue" in combined or "lappish" in combined:
        return "Head away from the city lights in search of the Northern Lights, with a Lappish barbecue and time by the fire in the winter landscape."
    if "hunt" in combined or "chase" in combined:
        return "Head out in search of the Northern Lights with local guidance, using the evening conditions to find the best available viewing areas."
    if "floating" in combined or "float" in combined:
        return "Experience the Arctic night from a peaceful frozen-lake setting, with specialist equipment provided for the ice-floating experience."
    return "Enjoy an evening Northern Lights experience designed around the Arctic sky, local conditions, and the chance to see the aurora."


__all__ = ["keyword_activity_description", "specific_activity_description"]
