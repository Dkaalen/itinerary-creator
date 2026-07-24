"""Canonical transport domain package.

Import the route-facts contract from this package when a caller needs
production transport truth.  Prose and rendering remain in their dedicated
submodules.
"""

from itinerary_generation.transport_domain.routes import TransportRouteFacts, get_transport_route_facts

__all__ = ["TransportRouteFacts", "get_transport_route_facts"]
