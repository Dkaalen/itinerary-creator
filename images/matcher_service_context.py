"""Infer service intents and visual themes from itinerary rows."""

from images.metadata import city_variants,infer_themes,normalize_keyword,tokenize

SERVICE_INTENT_KEYWORDS={"rail":{"train","rail","railway","flam","flåm","myrdal","nutshell"},"fjord_cruise":{"fjord","cruise","boat","lysefjord","preikestolen","naeroyfjord","nærøyfjord","flam","flåm","gudvangen"},"coastal_cruise":{"coastal","cruise","ferry","port","harbour","harbor","fjord","lounge"},"kayaking":{"kayak","kayaking","river","otra","paddle"},"city_walk":{"walking","walk","historic","old","town","guide","guided"},"funicular":{"funicular","floibanen","fløibanen","fløyen","floyen","mount","viewpoint"}}

def row_type(row:dict)->str:return normalize_keyword(row.get("effective_type") or row.get("type") or "")
def row_text(row:dict)->str:return " ".join((str(row.get("city","") or ""),str(row.get("title","") or ""),str(row.get("original_title","") or ""),str(row.get("details","") or ""),str(row.get("display_description","") or "")," ".join(row.get("includes",[]) or [])))

def service_intents_for_rows(rows:list[dict])->set[str]:
    intents=set();text=normalize_keyword(" ".join(row_text(row) for row in rows or []));tokens=tokenize(text);types={row_type(row) for row in rows or []}
    if "norway in a nutshell" in text or "nutshell" in tokens:intents.update({"scenic_rail_fjord","rail","fjord_cruise"})
    if tokens&{"lysefjord","preikestolen"}:intents.add("fjord_cruise")
    if "coastal cruise" in text or "atlantic coastal" in text:intents.add("coastal_cruise")
    if types&{"train"} or tokens&SERVICE_INTENT_KEYWORDS["rail"]:intents.add("rail")
    if types&{"cruise","ferry"} or tokens&{"fjord","cruise","boat"}:intents.add("fjord_cruise" if tokens&{"fjord","lysefjord","preikestolen","naeroyfjord","gudvangen","flam","flåm"} else "coastal_cruise")
    for name in ("kayaking","funicular","city_walk"):
        if tokens&SERVICE_INTENT_KEYWORDS[name]:intents.add(name)
    if types<={"arrival","departure","hotel","accommodation","leisure","transfer"} and not tokens&{"train","cruise","fjord","kayak","funicular"}:intents-={"coastal_cruise","fjord_cruise"}
    return intents

def service_destination_variants(intents:set[str],text:str)->set[str]:
    variants=set();normalized=normalize_keyword(text)
    if "scenic_rail_fjord" in intents or "norway in a nutshell" in normalized:
        for place in ("Bergen","Voss","Gudvangen","Flåm","Flam","Myrdal","Oslo","Nærøyfjord","Naeroyfjord"):variants.update(city_variants(place))
    if "fjord_cruise" in intents and ("lysefjord" in normalized or "preikestolen" in normalized):
        for place in ("Stavanger","Lysefjord","Preikestolen"):variants.update(city_variants(place))
    return variants

def themes_for_rows(rows:list[dict])->set[str]:
    parts=[];hinted=set()
    for row in rows or []:
        kind=row_type(row);text=row_text(row);tokens=tokenize(text);parts.append(text)
        if kind in {"hotel","accommodation","arrival","departure"}:hinted.add("city")
        if kind in {"transfer","transport","drive","car"}:
            if tokens&{"private","airport","hotel","station"}:hinted.add("city")
            if tokens&{"train","rail","railway","express","overnight"}:hinted.add("train")
            if tokens&{"coach","bus","road","route","drive","driving","vehicle","car"}:hinted.add("road journey")
    return infer_themes(tokenize(" ".join(parts)))|hinted
