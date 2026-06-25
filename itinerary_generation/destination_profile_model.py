"""Immutable value model for destination copy profiles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DestinationProfile:
    name: str
    country: str
    region: str
    destination_type: str
    copy_profile: str
    aliases: tuple[str, ...]
    identity: str
    arrival_identity: str
    leisure_identity: str
    atmosphere: tuple[str, ...]
    hooks: tuple[str, ...]
    arrival_templates: tuple[str, ...]
    leisure_templates: tuple[str, ...]
    departure_templates: tuple[str, ...]


__all__ = ["DestinationProfile"]
