"""Source identity and lookup helpers for structured-document validation."""

import re
from collections import defaultdict
from itinerary_generation.structured_model import SourceRowRef,StructuredListItem
from shared.commercial_markers import has_self_transfer_marker

REVIEW_KIND_COVERAGE={"activity","accommodation"};INCLUDED_STATUSES={"","included"}
STOP_TOKENS={"activity","admission","arranged","centre","center","city","cruise","day","duration","evening","experience","from","guided","hotel","included","includes","into","morning","night","only","private","self","the","ticket","tickets","time","tour","transfer","walk","walking","with","your","bergen","helsinki","ivalo","kakslauttenen","oslo","rovaniemi","tallinn","tromso","tromsø"}
SOURCE_SIGNAL_GROUPS=(("fjord","fjords","fjorden","fjord safari","fjordsafari"),("cruise","boat","sailing","ferry"),("museum","gallery","munch"),("walking","walk","city center","city centre"),("northern lights","aurora","auroras"),("husky","reindeer","safari"),("cable car","fjellheisen","funicular","funicual"))

def status_is_included(value:str)->bool:return str(value or "included").strip().lower() in INCLUDED_STATUSES
def compact_tokens(value:str)->set[str]:return {token for token in (item.lower() for item in re.findall(r"[A-Za-zÀ-ÿøØåÅäÄöÖæÆðÐþÞ]{4,}",str(value or ""))) if token not in STOP_TOKENS}

def source_text(source:SourceRowRef|None)->str:
    if source is None:return ""
    raw,normalized,original=str(source.raw_text or "").strip(),str(source.title or "").strip(),str(source.original_title or "").strip()
    if original and raw==normalized:raw=""
    return "\n".join(value for value in (original,raw,source.city) if str(value or "").strip())

def item_identity_text(item)->str:return "\n".join(value for value in (item.title,"\n".join(item.detail_lines or ()),item.destination) if str(value or "").strip())

def list_items_by_source(sections)->dict[str,list[StructuredListItem]]:
    mapping=defaultdict(list)
    for section in sections:
        for item in section.items:
            for row_id in item.source_row_ids:
                if row_id:mapping[row_id].append(item)
    return mapping

def source_requires_exclusion(source:SourceRowRef)->bool:
    status=str(source.commercial_status or "").strip().lower();reason=str(source.commercial_reason or "").strip().lower()
    if status in {"self_arranged","excluded","optional"} or reason in {"cost_not_included","self_arranged","optional"}:return True
    text="\n".join(value for value in (source.original_title,source.raw_text,source.title) if str(value or "").strip()).lower()
    return bool(has_self_transfer_marker(text) or "self arranged" in text or "self-arranged" in text or re.search(r"\b(?:price\s+not\s+included|cost\s+not\s+included|not\s+in(?:cl|lc)uded\s*[:?]|to\s+be\s+bought\s+on\s+site|paid\s+locally|pay\s+locally)\b",text,re.I))
