"""Typed models for remote image-bank distribution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DestinationRequest:
    destination: str
    country: str = ""

    @property
    def key(self) -> str:
        return f"{self.country}/{self.destination}" if self.country else self.destination


@dataclass(frozen=True, slots=True)
class ResolvedDestinationPack:
    manifest_key: str
    country: str
    destination: str
    asset_name: str
    download_url: str
    sha256: str
    file_count: int
    size_bytes: int


class DistributionError(RuntimeError):
    """Raised when a destination-pack distribution cannot be used safely."""
