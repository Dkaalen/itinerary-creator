"""Registry-owned fallback descriptions for matched products."""

from itinerary_generation.fjordtours_activity_catalogue import fjordtours_activity_description
from itinerary_generation.product_rule_models import ProductConfidence

DESCRIPTIONS={
"tallinn_old_town_guided_tour":"Explore Tallinn’s Old Town with a guide during your time ashore, with key landmarks and local context introduced along the walking route.",
"tallinn_ferry_framework":"Travel between Helsinki and Tallinn by ferry, with the crossings forming the logistics for your time in Tallinn.",
"munch_museum":"Visit the Munch Museum at your own pace, with pre-arranged admission giving you time to explore the galleries and exhibitions independently.",
"fjellheisen":"Use your round-trip Fjellheisen ticket for a flexible visit above Tromsø, with time to enjoy the panoramic views over the city, fjords and surrounding mountains.",
"tromso_viewpoint_ticket_possible_fjellheisen":"Use your pre-arranged ticket for a flexible viewpoint visit in Tromsø, with time to enjoy the surrounding views during the day.",
"santa_claus_friends":"Experience a festive family-friendly visit with Santa Claus, reindeer and elves, including seasonal activities, warm refreshments and time for a private Santa meeting where included.",
"korouoma_canyon":"Follow a guided hike through Korouoma Canyon, where frozen waterfalls, winter forest scenery and a warm outdoor food stop shape the experience.",
}

def product_description(rule_id:str,*,confidence:ProductConfidence="strong")->str:return DESCRIPTIONS.get(rule_id) or fjordtours_activity_description(rule_id) or ""
