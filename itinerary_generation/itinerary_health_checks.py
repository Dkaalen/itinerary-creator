"""Public compatibility facade for actionable itinerary health checks."""

from itinerary_generation.health_check_builder import build_itinerary_health_issues, summarize_itinerary_health_issues
from itinerary_generation.health_check_models import CRITICAL, INFO, REVIEW, ItineraryHealthIssue, ItineraryHealthSummary

__all__ = ["CRITICAL", "INFO", "REVIEW", "ItineraryHealthIssue", "ItineraryHealthSummary", "build_itinerary_health_issues", "summarize_itinerary_health_issues"]
