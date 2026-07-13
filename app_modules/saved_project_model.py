"""Dataclasses for versioned saved itinerary projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SavedProjectMetadata:
    project_id: str
    itinerary_name: str
    created_at: str
    updated_at: str
    status: str


@dataclass(frozen=True)
class SavedProjectSource:
    source_input: str
    source_hash: str


@dataclass(frozen=True)
class SavedItinerarySnapshot:
    snapshot_id: str
    created_at: str
    parsed_rows: list[dict[str, Any]] = field(default_factory=list)
    output_edits: dict[str, Any] = field(default_factory=dict)
    detail_level: str = "Rich descriptive"
    day_page_layout: str = "One day per page"


@dataclass(frozen=True)
class SavedProjectImageState:
    cover_image: dict[str, Any] = field(default_factory=dict)
    summary_image: dict[str, Any] = field(default_factory=dict)
    day_images: dict[str, Any] = field(default_factory=dict)
    pictures_added: bool = False


@dataclass(frozen=True)
class SavedProjectExportState:
    pdf_status: str = "Not created"
    last_exported_at: str = ""


@dataclass(frozen=True)
class SavedProjectCalculatorSnapshot:
    schema_version: int = 2
    kind: str = "booknordics_calculator_state"
    itinerary_name: str = ""
    number_of_pax: int | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    currency_rates: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SavedItineraryProject:
    saved_schema_version: int
    kind: str
    metadata: SavedProjectMetadata
    source: SavedProjectSource
    generated_baseline_snapshot: SavedItinerarySnapshot
    current_snapshot: SavedItinerarySnapshot
    image_state: SavedProjectImageState
    export_state: SavedProjectExportState
    output_brand: str = "agent"
    mode: str = "agent"
    calculator_snapshot: SavedProjectCalculatorSnapshot = field(default_factory=SavedProjectCalculatorSnapshot)
