"""Canonical transport domain package.

Submodules hold route extraction, transport facts, transport titles, travel-arrangement rendering,
parser title normalization, inclusion text and transport-specific exclusions.
Legacy modules re-export from these submodules while callers migrate.
"""

from itinerary_generation.transport_domain.facts import TransportFacts, build_transport_facts

__all__ = ["TransportFacts", "build_transport_facts"]
