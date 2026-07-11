"""Cached precedence-ordered matching of activity product rules."""

from functools import lru_cache
from itinerary_domain.activity_cache import freeze_activity_row,freeze_activity_values,thaw_activity_row,thaw_activity_values
from itinerary_domain.activity_products import fingerprint_activity
from itinerary_domain.product_rule_context import product_context,product_context_lower
from itinerary_domain.product_rule_descriptions import product_description
from itinerary_domain.product_rule_evidence import has_explicit_fjellheisen_evidence,has_explicit_munch_museum_evidence,is_weak_tromso_viewpoint_ticket
from itinerary_domain.product_rule_models import ProductConfidence,ProductRuleMatch,RULE_BY_ID
from itinerary_domain.tallinn import is_tallinn_ferry_framework,is_tallinn_old_town_guided_tour
from itinerary_domain.title_routes import _looks_like_norway_in_a_nutshell,_route_label_from_activity_text

def product_match(rule_id:str,*,title:str|None=None,confidence:ProductConfidence="strong",description:str="")->ProductRuleMatch:
    rule=RULE_BY_ID[rule_id];chosen=title if title is not None else (rule.strong_title if confidence=="strong" else rule.weak_title)
    return ProductRuleMatch(rule.rule_id,chosen,confidence,description or product_description(rule.rule_id,confidence=confidence),rule.warning_code if confidence=="weak" else "",rule.warning_message if confidence=="weak" else "")

@lru_cache(maxsize=4096)
def find_product_match_cached(row_snapshot,values_snapshot):
    row=thaw_activity_row(row_snapshot);values=thaw_activity_values(values_snapshot);lower=product_context_lower(row,*values)
    if not lower.strip():return None
    if row and is_tallinn_old_town_guided_tour(row,*values):return product_match("tallinn_old_town_guided_tour")
    if row and is_tallinn_ferry_framework(row,*values):return product_match("tallinn_ferry_framework")
    if has_explicit_munch_museum_evidence(row,*values):return product_match("munch_museum")
    if has_explicit_fjellheisen_evidence(row,*values):return product_match("fjellheisen")
    if is_weak_tromso_viewpoint_ticket(row,*values):return product_match("tromso_viewpoint_ticket_possible_fjellheisen",confidence="weak")
    product=fingerprint_activity(row,*values)
    if product and product.display_title:return ProductRuleMatch(product.canonical_family,product.display_title,product.confidence,product_description(product.canonical_family,confidence=product.confidence),"ambiguous_activity_title" if product.confidence=="weak" else "","Activity product was inferred from weak source evidence; confirm the exact product name before final output." if product.confidence=="weak" else "")
    if _looks_like_norway_in_a_nutshell(lower):return product_match("norway_in_a_nutshell",title=_route_label_from_activity_text(product_context(row,*values)))
    if "santa claus" in lower and "friends" in lower:return product_match("santa_claus_friends")
    if "korouoma" in lower:return product_match("korouoma_canyon",title="")
    return None

def find_product_match(row:dict|None=None,*values:object)->ProductRuleMatch|None:return find_product_match_cached(freeze_activity_row(row),freeze_activity_values(values))
def product_warning(row:dict|None=None,*values:object)->tuple[str,str]:
    match=find_product_match(row,*values);return (match.warning_code,match.warning_message) if match and match.is_weak else ("","")
