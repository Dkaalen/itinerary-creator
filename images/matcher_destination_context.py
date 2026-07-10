"""Resolve destination, country and registry profiles for image matching."""

from itinerary_generation.destination_registry import destination_country_for_alias,destination_for_alias
from images.metadata import CITY_ALIASES,city_variants,normalize_keyword
from itinerary_generation.activity_location_contract import activity_location_facts

CITY_TO_COUNTRY={"oslo":"norway","bergen":"norway","kristiansand":"norway","stavanger":"norway","tromso":"norway","tromsø":"norway","flam":"norway","flåm":"norway","alesund":"norway","ålesund":"norway","helsinki":"finland","rovaniemi":"finland","kakslauttanen":"finland","kakslauttenen":"finland","ivalo":"finland","tallinn":"estonia","stockholm":"sweden","kiruna":"sweden","abisko":"sweden","gallivare":"sweden","gällivare":"sweden","copenhagen":"denmark","kobenhavn":"denmark","københavn":"denmark","reykjavik":"iceland","reykjavík":"iceland","keflavik":"iceland","keflavík":"iceland","vik":"iceland","vík":"iceland","hella":"iceland","hofn":"iceland","höfn":"iceland","akureyri":"iceland"}

def country_variants_for_city(city:str)->set[str]:
    variants=set()
    for value in city_variants(city):
        country=destination_country_for_alias(value) or CITY_TO_COUNTRY.get(normalize_keyword(value),"")
        if country:variants.add(country)
    return variants

def destination_profiles_for_city(city:str)->tuple[set[str],set[str]]:
    images,seasons=set(),set()
    for value in city_variants(city):
        record=destination_for_alias(value)
        if record:
            if record.image_profile:images.add(record.image_profile)
            if record.season_profile:seasons.add(record.season_profile)
    return images,seasons

def known_destination_from_text(text:str,current_city:str="")->str:
    normalized=normalize_keyword(text);current=city_variants(current_city)
    if not normalized:return ""
    facts=activity_location_facts(title=text, city=current_city, source_text=text)
    if facts.excursion_region and not (current & city_variants(facts.excursion_region)):
        return facts.excursion_region
    for canonical,aliases in sorted(CITY_ALIASES.items(),key=lambda item:-max(len(str(alias)) for alias in item[1])):
        values={normalize_keyword(alias) for alias in aliases}
        if current&values:continue
        for alias in values:
            if alias and any(pattern in normalized for pattern in (f"to {alias}",f"in {alias}",f"old town {alias}",f"{alias} old town",f"{alias} day trip",f"day trip to {alias}",f"excursion to {alias}")):return canonical.title() if canonical.isascii() else canonical
    return ""

def all_city_variants(rows:list[dict],primary:str,row_type_func)->set[str]:
    variants=set(city_variants(primary))
    for row in rows or []:
        city=str(row.get("city","") or "").strip()
        if city and row_type_func(row) in {"activity","hotel","accommodation","day overview"}:variants.update(city_variants(city))
    return variants
