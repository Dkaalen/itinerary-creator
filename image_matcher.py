"""
image_matcher.py

Compatibility wrapper for itinerary image matching.

The implementation now lives in the split images package:
    images/metadata.py
    images/scanner.py
    images/fallback.py
    images/matcher.py
    images/diagnostics.py

Keep importing from this file for backwards compatibility.
"""

from __future__ import annotations

from images import *  # noqa: F401,F403
