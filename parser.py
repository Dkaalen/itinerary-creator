"""Compatibility shim. The parser module was renamed to itinerary_parser.py.

New code should import from itinerary_parser instead of parser.
"""

from itinerary_parser import *  # noqa: F401,F403
