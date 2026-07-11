"""Value models for activity-training catalogue entries."""

from dataclasses import dataclass
import re
from itinerary_domain.activity_training_text import ascii_key, normalize_training_text


@dataclass(frozen=True)
class ActivityTrainingEntry:
    city: str; title: str; time: str=""; meeting_point: str=""; inclusions: tuple[str,...]=(); description: str=""; source_line: str=""
    @property
    def display_title(self)->str:return self.title
    @property
    def canonical_family(self)->str:return "catalogue_"+re.sub(r"[^a-z0-9]+","_",ascii_key(f"{self.city}_{self.title}")).strip("_")
    @property
    def product_type(self)->str:
        lower=normalize_training_text(f"{self.title} {' '.join(self.inclusions)} {self.description}")
        if "northern lights" in lower or "aurora" in lower:return "northern_lights"
        if "walking" in lower or "on foot" in lower:return "walking_tour"
        if any(x in lower for x in ("fjord","cruise","boat","canal","ferry")):return "cruise_or_boat"
        if any(x in lower for x in ("ticket","admission","entrance","pass")):return "ticket"
        if any(x in lower for x in ("hike","hiking","snowshoe")):return "outdoor_activity"
        if any(x in lower for x in ("reindeer","husky","santa")):return "arctic_activity"
        return "activity"


@dataclass(frozen=True)
class IndexedActivityTrainingEntry:
    entry: ActivityTrainingEntry; city_key: str; title_normalized: str; title_tokens: frozenset[str]
