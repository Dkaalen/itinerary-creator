"""Internal parser detail-helper namespace.

Raw parsing composes focused extraction helpers here.  Semantic classification
and client-facing source-row standardization belong to downstream domain and
normalizer owners.
"""

from parser_modules.detail_extractors import (  # noqa: F401
    extract_between_markers,
    extract_detail,
)
from parser_modules.title_cleanup import (  # noqa: F401
    _best_title_source,
    _looks_like_product_title,
    _split_long_title_from_prose,
    _strip_admin_title_prefixes,
    _strip_repeated_city_prefix,
    clean_title,
)
from parser_modules.list_parsing import split_comma_list  # noqa: F401
