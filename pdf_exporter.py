"""Compatibility wrapper for the split PDF exporter modules.

The implementation lives in :mod:`pdf_exporter_modules.public_api`; this file
keeps legacy imports from ``pdf_exporter.py`` working without eager rendering imports.
"""

from pdf_exporter_modules.public_api import __all__, __dir__, __getattr__
