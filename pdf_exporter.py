"""Compatibility wrapper for the split PDF exporter modules.

The implementation lives in :mod:`pdf_exporter_modules.public_api`; this file
keeps legacy imports from ``pdf_exporter.py`` working.
"""

from pdf_exporter_modules import public_api as _public_api

__all__ = _public_api.__all__
globals().update({name: getattr(_public_api, name) for name in __all__})
