"""Public compatibility facade for product-rule matching and copy."""

from itinerary_domain.product_rule_context import product_context,product_context_lower,product_source_context,product_source_context_lower
from itinerary_domain.product_rule_descriptions import product_description
from itinerary_domain.product_rule_evidence import has_explicit_fjellheisen_evidence,has_explicit_munch_museum_evidence,is_weak_tromso_viewpoint_ticket
from itinerary_domain.product_rule_matcher import find_product_match,find_product_match_cached as _find_product_match_cached,product_warning
from itinerary_domain.product_rule_models import PRODUCT_RULES,ProductConfidence,ProductRule,ProductRuleMatch

def clear_product_rule_cache()->None:_find_product_match_cached.cache_clear()
def product_rule_cache_info():return _find_product_match_cached.cache_info()

__all__=["PRODUCT_RULES","ProductConfidence","ProductRule","ProductRuleMatch","product_context","product_context_lower","product_source_context","product_source_context_lower","has_explicit_munch_museum_evidence","has_explicit_fjellheisen_evidence","is_weak_tromso_viewpoint_ticket","find_product_match","clear_product_rule_cache","product_rule_cache_info","product_description","product_warning"]
