"""High-confidence and weak-evidence predicates for named products."""

import re
from itinerary_domain.product_rule_context import product_source_context_lower,titleish_source_context

def has_explicit_munch_museum_evidence(row:dict|None=None,*values:object)->bool:
    titleish=titleish_source_context(row,*values).lower()
    if "munch" in titleish and "museum" in titleish:return True
    source=product_source_context_lower(row,*values)
    if not ("munch" in source and "museum" in source):return False
    explicit=re.search(r"(?:munch\s+museum[^.\n]{0,80}\b(?:ticket|tickets|admission|entry|visit)\b|\b(?:ticket|tickets|admission|entry|visit)\b[^.\n]{0,80}munch\s+museum)",source,re.I)
    incidental=re.search(r"(?:pass(?:ing)?|near|near to|close to|coastline|view of|stop at)\b[^.\n]{0,120}munch\s+museum",source,re.I)
    return bool(explicit and not incidental)

def has_explicit_fjellheisen_evidence(row:dict|None=None,*values:object)->bool:
    lower=product_source_context_lower(row,*values)
    return "fjellheisen" in lower or ("trom" in lower and any(marker in lower for marker in ("cable car","gondola","mountain lift","mountain cable","aerial tramway")))

def is_weak_tromso_viewpoint_ticket(row:dict|None=None,*values:object)->bool:
    lower=product_source_context_lower(row,*values)
    return "round trip ticket" in lower and "trom" in lower and not has_explicit_fjellheisen_evidence(row,*values)
