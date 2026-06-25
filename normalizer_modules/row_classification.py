"""Detect suspicious cities and misclassified accommodation rows."""

import re
import diagnostics
from place_aliases import is_likely_service_text,is_known_place
from normalizer_modules.text_utils import clean_space,get_row_type,text_blob

def looks_like_misclassified_hotel_row(row:dict)->bool:
    if get_row_type(row) not in {"Transfer","Transport"}:return False
    full=text_blob(row).lower()
    if re.search(r"\b(?:airport|station|bus\s*station|hotel)\s+to\s+(?:airport|station|bus\s*station|hotel)\b",full) or re.search(r"\b(?:private|shared)\s+(?:airport|station|hotel)\s+to\s+(?:airport|station|bus\s*station|hotel)\b",full):return False
    accommodation=re.search(r"\b[2-5]\s*[- ]?star\b",full) and re.search(r"\b\d+\s*(?:x\s*)?(?:night|ngiht|nite|nt)s?\b",full);room=re.search(r"\b(?:standard|superior|deluxe|double|twin|family|room|igloo|aurora\s+nest|suite|cabin|incl\s+brek?afast|breakfast)\b",full);hotel=re.search(r"\b(?:hotel|resort|scandic|comfort|clarion|radisson|thon|igloo|spa)\b",full)
    return bool((accommodation and (room or hotel)) or (hotel and room and re.search(r"\b\d+\s*(?:x\s*)?(?:night|ngiht|nite|nt)s?\b",full)))

def warn_suspicious_city(row:dict)->None:
    city=clean_space(row.get("city",""))
    if not city:return
    lower=city.lower()
    if is_likely_service_text(city) or any(marker in lower for marker in ("ticket","option","sightseeing","private tour","hop on","hop-off","cancel")):
        diagnostics.warn("suspicious_city",f"Suspicious city value '{city}' on {row.get('day','Unknown day')} — check source columns.",raw_value=row.get("raw",city));row["city"]="";return
    if not is_known_place(city) and len(city)>18:diagnostics.warn("unrecognised_city",f"City '{city}' on {row.get('day','Unknown day')} is not in the known place list — verify it is correct.",raw_value=row.get("raw",city))
