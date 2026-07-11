"""Conservative cached matching against activity-training entries."""

from functools import lru_cache
from itinerary_domain.activity_training_loader import activity_training_entries
from itinerary_domain.activity_training_model import ActivityTrainingEntry,IndexedActivityTrainingEntry
from itinerary_domain.activity_training_text import normalize_training_text,training_tokens
from place_aliases import canonicalize_place_name

ANCHORS={"northern_lights","base_camp","snowmobile","reindeer","husky","santa","suomenlinna","fløibanen","fjord","cruise","walking","korouoma","ranua","tallinn","nutshell"}

@lru_cache(maxsize=1)
def activity_training_index():return tuple(IndexedActivityTrainingEntry(e,normalize_training_text(e.city),normalize_training_text(e.title),training_tokens(e.title)) for e in activity_training_entries())

@lru_cache(maxsize=4096)
def match_activity_training_entry_cached(source_text,source_city_key,source_title_text,min_score):
    title_tokens=training_tokens(source_title_text or source_text);source_tokens=training_tokens(source_text);best=None
    if not source_tokens:return None
    for indexed in activity_training_index():
        if source_city_key and indexed.city_key and source_city_key!=indexed.city_key:continue
        tokens=indexed.title_tokens
        if not tokens:continue
        direct=bool(indexed.title_normalized and (indexed.title_normalized in source_text or source_text in indexed.title_normalized));comparison=title_tokens or source_tokens;overlap=len(tokens&comparison);score=1.0 if direct else .72*overlap/max(len(tokens),1)+.28*overlap/max(len(comparison),1)
        if score>=min_score and (direct or bool(tokens&source_tokens&ANCHORS)) and (best is None or score>best[0]):best=(score,indexed.entry)
    return best[1] if best else None

def match_activity_training_entry(source: str,*,city: str="",source_title: str="",min_score: float=.72)->ActivityTrainingEntry|None:
    source_text=normalize_training_text(" ".join(part for part in (source_title,source) if part))
    if not source_text:return None
    canonical=canonicalize_place_name(city or "")
    return match_activity_training_entry_cached(source_text,normalize_training_text(canonical or city or ""),normalize_training_text(source_title or source),float(min_score))

def catalogue_description_for_row(row:dict)->str:
    source=" ".join(str(row.get(k,"") or "") for k in ("original_title","title","details","description"));entry=match_activity_training_entry(source,city=str(row.get("city","") or ""),source_title=str(row.get("original_title") or row.get("title") or ""));return entry.description if entry and entry.description else ""
