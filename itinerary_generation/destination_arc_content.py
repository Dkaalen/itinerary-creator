"""Journey Arc fallback copy for destinations."""
from __future__ import annotations

from itinerary_generation.destination_registry import NordicDestination
from itinerary_generation.destination_seasonal_variants import destination_copy_profile

CAPITAL_OVERRIDES: dict[str, str] = {
    "Oslo": "Discover the Norwegian capital",
    "Stockholm": "Stockholm islands and old town",
    "Copenhagen": "Copenhagen design and harbour life",
    "Helsinki": "Helsinki design and waterfront life",
    "Reykjavík": "Reykjavík culture and coastal colour",
}

DESTINATION_ARC_OVERRIDES: dict[str, str] = {
    **CAPITAL_OVERRIDES,
    "Kristiansand": "Southern coastal charm",
    "Stavanger": "Stavanger harbour and fjord gateway",
    "Bergen": "Bergen harbour and mountain views",
    "Tromsø": "Arctic city and northern landscapes",
    "Alta": "Arctic nature and Northern Lights country",
    "Rovaniemi": "Lapland forest and Arctic Circle atmosphere",
    "Flåm": "Fjord village and railway scenery",
    "Voss": "Mountain village and fjordland adventure",
    "Geiranger": "Geirangerfjord views and village atmosphere",
    "Ålesund": "Art Nouveau streets and coastal views",
    "Svolvær": "Lofoten harbour and mountain scenery",
    "Reine": "Lofoten fishing village and dramatic peaks",
    "Trondheim": "Historic Trondheim and fjordside streets",
    "Kiruna": "Swedish Lapland and Arctic landscapes",
    "Abisko": "Arctic national park and mountain views",
    "Åre": "Mountain village and alpine scenery",
    "Visby": "Medieval walls and Baltic island atmosphere",
    "Gothenburg": "Gothenburg canals and coastal culture",
    "Malmö": "Modern city life and Öresund connections",
    "Turku": "Archipelago gateway and riverside history",
    "Tampere": "Lakeland city and industrial heritage",
    "Levi": "Lapland resort and fell scenery",
    "Saariselkä": "Arctic fells and wilderness atmosphere",
    "Porvoo": "Old wooden streets and riverside charm",
    "Åland": "Archipelago islands and maritime calm",
    "Aarhus": "Jutland culture and waterfront city life",
    "Odense": "Fairytale heritage and Funen charm",
    "Aalborg": "North Jutland harbour and city culture",
    "Billund": "Family-friendly Jutland gateway",
    "Roskilde": "Viking heritage and fjord views",
    "Helsingør": "Castle town and Øresund views",
    "Skagen": "Northern light and seaside atmosphere",
    "Bornholm": "Baltic island villages and coastal scenery",
    "Keflavík": "Reykjanes coast and arrival gateway",
    "Blue Lagoon": "Geothermal lagoon and Reykjanes lava fields",
    "Golden Circle": "Iceland’s classic waterfall and geyser route",
    "South Coast": "Waterfalls, black sands and glacier views",
    "Vík": "Black-sand coast and South Iceland scenery",
    "Jökulsárlón": "Glacier lagoon and floating icebergs",
    "Skaftafell": "Glacier landscapes and national park trails",
    "Vatnajökull": "Glacier wilderness and volcanic landscapes",
    "Akureyri": "North Iceland culture and fjord setting",
    "Mývatn": "Volcanic lake landscapes and geothermal scenery",
    "Húsavík": "Whale-watching harbour and North Iceland coast",
    "Snæfellsnes": "Peninsula scenery and coastal villages",
    "Ísafjörður": "Westfjords harbour and mountain setting",
    "Westfjords": "Remote fjords and dramatic coastal scenery",
    "Landmannalaugar": "Highland colours and rhyolite mountains",
    "Ring Road": "Iceland’s full scenic circuit",
}

PROFILE_ARC_TEMPLATES: dict[str, str] = {
    "coastal_city": "{name} coastal character and harbour life",
    "urban_culture": "{name} culture and city life",
    "arctic": "{name} Arctic landscapes and northern atmosphere",
    "scenic_nature": "{name} scenery and local nature",
    "mountain_resort": "{name} mountain scenery and resort atmosphere",
    "national_park": "{name} national park landscapes",
    "scenic_route": "{name} scenic route",
    "icelandic_town": "{name} Icelandic landscapes and local life",
    "icelandic_nature": "{name} dramatic Icelandic nature",
    "icelandic_landmark": "{name} Icelandic landmark scenery",
    "thermal_lagoon": "{name} geothermal lagoon experience",
    "destination": "{name} regional character and local scenery",
}


def arc_for_destination(name: str, record: NordicDestination | None) -> str:
    if record and record.name in DESTINATION_ARC_OVERRIDES:
        return DESTINATION_ARC_OVERRIDES[record.name]
    if name in DESTINATION_ARC_OVERRIDES:
        return DESTINATION_ARC_OVERRIDES[name]
    profile = destination_copy_profile(record)
    template = PROFILE_ARC_TEMPLATES.get(profile, PROFILE_ARC_TEMPLATES["destination"])
    return template.format(name=name)

