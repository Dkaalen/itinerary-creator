"""Compatibility exports for parser detail helpers.

The implementation lives in smaller modules grouped by responsibility. Keep
these imports so existing callers can continue importing from parser_modules.details.
"""

from parser_modules.row_text_standardization import (  # noqa: F401
    _fix_common_text_for_context,
    standardize_row_text,
)
from parser_modules.detail_extractors import (  # noqa: F401
    _looks_like_cruise_experience_text,
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
from parser_modules.effective_type_detection import detect_effective_type  # noqa: F401
