"""Cached file loaders for the versioned reference corpus."""

import csv
import json
from functools import lru_cache
from pathlib import Path

from itinerary_generation.reference_corpus_models import CleanActivityReference, StandardInputTemplate

CORPUS_VERSION = "ih1-v1"
SCHEMA_VERSION = 1
CORPUS_ROOT = Path(__file__).resolve().parent / "data" / "reference_corpus" / CORPUS_VERSION
STANDARD_PATH = CORPUS_ROOT / "standard_input_templates.tsv"
ACTIVITY_PATH = CORPUS_ROOT / "clean_activity_inputs.tsv"
ICELAND_PATH = CORPUS_ROOT / "iceland_standard_itinerary.json"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"


def split_semicolon(value: str) -> tuple[str, ...]:
    return tuple(item for item in (part.strip() for part in str(value or "").split(";")) if item)


@lru_cache(maxsize=1)
def standard_input_templates() -> tuple[StandardInputTemplate, ...]:
    with STANDARD_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(StandardInputTemplate(row["record_id"], row["service_type"], row["source_destination"], row["canonical_destination"], row["template_text"], split_semicolon(row["placeholders"])) for row in csv.DictReader(handle, delimiter="\t"))


@lru_cache(maxsize=1)
def clean_activity_references() -> tuple[CleanActivityReference, ...]:
    with ACTIVITY_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(CleanActivityReference(row["record_id"], row["record_type"], row["source_city"], row["canonical_city"], row["activity_location"], row["canonical_activity_location"], row["activity_text"], split_semicolon(row["conditional_markers"])) for row in csv.DictReader(handle, delimiter="\t"))


@lru_cache(maxsize=1)
def iceland_reference_payload() -> dict:
    return json.loads(ICELAND_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def reference_corpus_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
