"""Stable public facade for fact-based itinerary day intros."""
from itinerary_generation.day_intro_rendering import plan_day_intro_decision, write_day_intro

__all__ = ["plan_day_intro_decision", "write_day_intro"]
