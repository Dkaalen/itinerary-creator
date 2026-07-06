"""Compatibility wrapper for itinerary generation helpers.

The implementation lives in :mod:`itinerary_generation.public_api`; this file
keeps legacy imports from ``generator.py`` working.
"""

from itinerary_generation import public_api as _public_api

__all__ = _public_api.__all__
globals().update({name: getattr(_public_api, name) for name in __all__})
