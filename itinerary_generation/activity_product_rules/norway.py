"""Compatibility facade for :mod:`itinerary_domain.activity_product_rules.norway`.

Neutral source truth moved out of the generation layer. New parser and
normalizer code must import the neutral owner directly.
"""

from importlib import import_module as _import_module

_impl = _import_module("itinerary_domain.activity_product_rules.norway")
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

__all__ = getattr(
    _impl,
    "__all__",
    tuple(name for name in globals() if not name.startswith("_")),
)
