"""Neutral itinerary truth contracts shared by parsing and generation.

This package owns source-backed product, route, title-cleaning and group-tour
truth. Rendering modules may consume these contracts, but parser/normalizer
code no longer imports the generation layer to discover neutral facts.
"""
