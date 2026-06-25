"""Copy data used to build deterministic destination profiles."""

COUNTRY_ADJECTIVE = {
    "Norway": "Norwegian", "Sweden": "Swedish", "Finland": "Finnish",
    "Denmark": "Danish", "Iceland": "Icelandic",
}

IDENTITY_OVERRIDES: dict[str, str] = {
    "Oslo": "the Norwegian capital", "Bergen": "this historic harbour city and fjord gateway",
    "Stavanger": "Norway’s fjord gateway and old wooden city", "Kristiansand": "Southern Norway’s coastal city",
    "Tromsø": "Norway’s Arctic capital", "Trondheim": "this historic fjordside city",
    "Ålesund": "this Art Nouveau coastal city", "Flåm": "this fjord village beneath the mountains",
    "Voss": "this mountain village between fjords and valleys", "Geiranger": "this village at the heart of Geirangerfjord",
    "Reine": "this Lofoten fishing village beneath dramatic peaks", "Svolvær": "this Lofoten harbour town",
    "Longyearbyen": "this High Arctic settlement in Svalbard", "Stockholm": "Sweden’s island capital",
    "Gothenburg": "Sweden’s west-coast harbour city", "Malmö": "this southern Swedish city by the Øresund",
    "Kiruna": "this Swedish Lapland gateway", "Abisko": "this Arctic national-park village",
    "Åre": "this Swedish mountain village", "Visby": "this medieval Baltic island town",
    "Helsinki": "Finland’s design-minded waterfront capital", "Rovaniemi": "this Lapland city on the Arctic Circle",
    "Turku": "Finland’s riverside archipelago gateway", "Tampere": "this Finnish lakeland city",
    "Levi": "this Finnish Lapland fell resort", "Saariselkä": "this Arctic fell village",
    "Porvoo": "this riverside town of old wooden streets", "Åland": "this calm Nordic archipelago",
    "Copenhagen": "the Danish capital of design, canals and harbour life", "Aarhus": "this Jutland city of culture and waterfront life",
    "Odense": "this Funen city of fairytale heritage", "Aalborg": "this North Jutland harbour city",
    "Billund": "this family-friendly Jutland gateway", "Roskilde": "this Viking city by the fjord",
    "Helsingør": "this castle town by the Øresund", "Skagen": "this northern Danish seaside town",
    "Bornholm": "this Baltic island of villages and coastline", "Reykjavík": "Iceland’s compact coastal capital",
    "Keflavík": "this Reykjanes arrival gateway", "Blue Lagoon": "this geothermal lagoon in the lava fields",
    "Golden Circle": "Iceland’s classic waterfall, geyser and national-park route",
    "South Coast": "Iceland’s waterfall, glacier and black-sand coast", "Vík": "this South Iceland village by the black-sand coast",
    "Jökulsárlón": "this glacier lagoon of drifting icebergs", "Skaftafell": "this Vatnajökull national-park landscape",
    "Vatnajökull": "this vast Icelandic glacier wilderness", "Akureyri": "North Iceland’s fjordside capital",
    "Mývatn": "this volcanic lake landscape in North Iceland", "Húsavík": "this North Iceland whale-watching harbour",
    "Snæfellsnes": "this peninsula of coastal villages and volcanic scenery",
    "Ísafjörður": "this Westfjords harbour town beneath the mountains", "Westfjords": "Iceland’s remote fjords and dramatic coast",
    "Landmannalaugar": "this highland area of colourful rhyolite mountains", "Ring Road": "Iceland’s full scenic circuit",
}

ATMOSPHERE_OVERRIDES: dict[str, tuple[str, ...]] = {
    "Oslo": ("the harbourfront and waterfront neighbourhoods", "museums, galleries and modern Nordic architecture", "capital streets, green city spaces and fjordside cafés"),
    "Bergen": ("Bryggen and the harbourfront", "colourful wooden streets and hillside viewpoints", "Fløyen views, local cafés and fjord-gateway atmosphere"),
    "Stavanger": ("the harbourfront and old wooden streets", "local cafés around the centre", "an easy evening in Norway’s fjord gateway"),
    "Kristiansand": ("the harbourfront and southern coastal streets", "time by the sea", "local cafés in Southern Norway’s coastal city"),
    "Tromsø": ("Arctic waterfront views", "northern cafés and compact city streets", "mountain scenery around the city"),
    "Rovaniemi": ("riverside paths and Lapland atmosphere", "northern design shops and local cafés", "time to settle into the Arctic Circle setting"),
    "Copenhagen": ("canals, harbour baths and waterfront streets", "design shops, cafés and historic squares", "neighbourhood life around the Danish capital"),
    "Stockholm": ("island viewpoints and waterfront walks", "Gamla Stan, museums and local cafés", "harbour life across the Swedish capital"),
    "Helsinki": ("waterfront markets and design districts", "harbour views, architecture and local cafés", "easy walks through Finland’s capital"),
    "Reykjavík": ("colourful streets and coastal viewpoints", "local cafés, galleries and harbour life", "time to settle into Iceland’s capital"),
}

PROFILE_ATMOSPHERE: dict[str, tuple[str, ...]] = {
    "coastal_city": ("the harbourfront", "coastal streets and viewpoints", "waterfront cafés and small shops"),
    "urban_culture": ("historic streets", "museums, galleries or design shops", "local cafés and city viewpoints"),
    "arctic": ("Arctic scenery", "local cafés and a slower northern pace", "the waterfront or village centre"),
    "scenic_nature": ("nearby viewpoints", "village streets or waterside paths", "the surrounding fjord, lake or valley scenery"),
    "mountain_resort": ("mountain views around the resort", "local cafés and resort village atmosphere", "time between outdoor experiences"),
    "national_park": ("viewpoints and visitor areas", "trails and surrounding landscapes", "a calm pause between nature experiences"),
    "scenic_route": ("scenic stops along the route", "viewpoints and short photo pauses", "the changing landscapes"),
    "icelandic_town": ("the town centre and harbour area", "local cafés and Icelandic village life", "nearby coastal or lava-field views"),
    "icelandic_nature": ("viewpoints and wide-open landscapes", "short scenic pauses", "the surrounding volcanic scenery"),
    "icelandic_landmark": ("viewpoints around the landmark", "time for photos and surrounding scenery", "a relaxed pause before continuing the route"),
    "thermal_lagoon": ("time to slow down in the geothermal setting", "nearby lava-field views", "a calm pause before continuing the journey"),
    "destination": ("local streets and viewpoints", "small local stops", "the surrounding scenery"),
}

PROFILE_HOOKS: dict[str, tuple[str, ...]] = {
    "coastal_city": ("harbour", "coast", "waterfront"), "urban_culture": ("culture", "architecture", "local neighbourhoods"),
    "arctic": ("Arctic setting", "northern light", "winter landscapes"), "scenic_nature": ("fjord scenery", "mountain views", "village atmosphere"),
    "mountain_resort": ("mountain scenery", "outdoor life", "resort atmosphere"), "national_park": ("protected landscapes", "viewpoints", "trails"),
    "scenic_route": ("changing landscapes", "route highlights", "photo stops"), "icelandic_town": ("harbour", "coast", "local Icelandic life"),
    "icelandic_nature": ("volcanic scenery", "wide-open landscapes", "waterfalls or glaciers"), "icelandic_landmark": ("landmark scenery", "viewpoints", "weather-shaped landscapes"),
    "thermal_lagoon": ("geothermal water", "lava fields", "slow travel"), "destination": ("local character", "scenery", "independent time"),
}

ARRIVAL_TEMPLATES = (
    "After check-in, the rest of the day is yours to settle in, relax, and enjoy your first impressions of {identity}.",
    "Once settled, keep the rest of the day relaxed, with time to get a first feel for {identity}.",
    "After check-in, the day stays unhurried so you can settle in and begin getting a sense of {identity}.",
)
LEISURE_TEMPLATES = (
    "Use the remaining time in {city} at your own pace, whether you prefer {focus}.",
    "Use the remaining time in {city} flexibly, with space for {focus}.",
    "Use the remaining time in {city} unhurriedly, leaving room for {focus}.",
)
DEPARTURE_TEMPLATES = (
    "After check-out, say farewell to {identity} before continuing your onward journey.",
    "Your time in {city} comes to a close today, with departure arrangements kept simple after check-out.",
)
