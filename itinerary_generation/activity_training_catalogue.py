"""Bundled activity training catalogue and conservative matching helpers.

The catalogue is generated from real messy supplier rows and their cleaned
client-facing equivalents.  It is not a replacement for explicit product rules;
instead it provides high-confidence examples that help the parser/normalizer
preserve source fidelity for known product families and compose better output
for rows that arrive in a new supplier format.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import csv
import re
import unicodedata

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title

_DATA_PATH = Path(__file__).resolve().parent / "data" / "activity_training_master_3col.tsv"

_STOPWORDS = {
    "a", "an", "and", "at", "by", "day", "for", "from", "in", "incl", "including",
    "of", "on", "or", "the", "to", "tour", "trip", "with", "without", "experience",
    "activity", "ticket", "tickets", "entry", "admission", "only", "included", "includes",
}

_TOKEN_SYNONYMS = {
    "aurora": "northern lights",
    "basecamp": "base camp",
    "sami": "sámi",
    "saami": "sámi",
    "floibanen": "fløibanen",
    "flam": "flåm",
    "tromso": "tromsø",
    "reykjavik": "reykjavík",
    "alesund": "ålesund",
    "svolvaer": "svolvær",
    "saariselka": "saariselkä",
    "kakslauttenen": "kakslauttanen",
    "tallin": "tallinn",
    "nutsheel": "nutshell",
    "nutshelll": "nutshell",
}


@dataclass(frozen=True)
class ActivityTrainingEntry:
    """One canonical activity row from the bundled training catalogue."""

    city: str
    title: str
    time: str = ""
    meeting_point: str = ""
    inclusions: tuple[str, ...] = ()
    description: str = ""
    source_line: str = ""

    @property
    def display_title(self) -> str:
        return self.title

    @property
    def canonical_family(self) -> str:
        return "catalogue_" + re.sub(r"[^a-z0-9]+", "_", _ascii_key(f"{self.city}_{self.title}")).strip("_")

    @property
    def product_type(self) -> str:
        lower = _normalize_text(f"{self.title} {' '.join(self.inclusions)} {self.description}")
        if "northern lights" in lower or "aurora" in lower:
            return "northern_lights"
        if "walking" in lower or "on foot" in lower:
            return "walking_tour"
        if any(marker in lower for marker in ("fjord", "cruise", "boat", "canal", "ferry")):
            return "cruise_or_boat"
        if any(marker in lower for marker in ("ticket", "admission", "entrance", "pass")):
            return "ticket"
        if any(marker in lower for marker in ("hike", "hiking", "snowshoe")):
            return "outdoor_activity"
        if any(marker in lower for marker in ("reindeer", "husky", "santa")):
            return "arctic_activity"
        return "activity"


def _ascii_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.lower()


def _normalize_text(value: str) -> str:
    text = str(value or "").replace("\xa0", " ").lower()
    for source, replacement in _TOKEN_SYNONYMS.items():
        text = re.sub(rf"\b{re.escape(source)}\b", replacement, text, flags=re.I)
    text = re.sub(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:hrs?|hours?|minutes?|mins?)\b", " ", text, flags=re.I)
    text = re.sub(r"[^a-z0-9åäöøæéáíóúýþðàèìòùñçšžœßà-ÿ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: str) -> set[str]:
    normalized = _normalize_text(value)
    tokens = {token for token in normalized.split() if len(token) > 2 and token not in _STOPWORDS}
    # Keep multi-word synonym signal as individual tokens too.
    if "northern" in tokens and "lights" in tokens:
        tokens.add("northern_lights")
    if "base" in tokens and "camp" in tokens:
        tokens.add("base_camp")
    return tokens


def _field_from_details(details: str, label: str) -> str:
    pattern = re.compile(
        rf"\s+-\s+{re.escape(label)}\s*:\s*(.*?)(?=\s+-\s+(?:Time|Meeting point|Inclusions|Description)\s*:|$)",
        flags=re.I | re.S,
    )
    match = pattern.search(details)
    return polish_client_text(match.group(1).strip()) if match else ""


def _title_from_details(city: str, details: str) -> str:
    text = str(details or "").strip()
    if city and text.lower().startswith(f"{city.lower()}:"):
        text = text.split(":", 1)[1].strip()
    text = re.split(r"\s+-\s+Time\s*:", text, maxsplit=1, flags=re.I)[0].strip(" -:|")
    title = polish_title(text)
    if re.search(r"aurora\s+basecamp|aurora\s+base\s+camp", text, flags=re.I):
        title = re.sub(r"Northern Lights Basecamp", "Aurora Basecamp", title, flags=re.I)
        title = re.sub(r"Northern Lights Base Camp", "Aurora Basecamp", title, flags=re.I)
    return title


def _split_inclusions(value: str) -> tuple[str, ...]:
    if not value or value.lower() == "not specified":
        return ()
    parts = re.split(r"\s*;\s*|\s*,\s*(?=(?:professional|english|knowledgeable|round|hotel|transport|pick|drop|warm|snacks|drinks|ticket|guided|visit|cruise|free|lunch|meal|thermal|winter|hot|snow|reindeer|husky|santa|short|storytelling|traditional)\b)", value, flags=re.I)
    cleaned = []
    for part in parts:
        item = polish_client_text(part).strip(" .;,-")
        if item and item not in cleaned and item.lower() != "not specified":
            cleaned.append(item)
    return tuple(cleaned)


@lru_cache(maxsize=1)
def activity_training_entries() -> tuple[ActivityTrainingEntry, ...]:
    if not _DATA_PATH.exists():
        return ()
    entries: list[ActivityTrainingEntry] = []
    with _DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if (row.get("Activity") or "").strip().lower() != "activity":
                continue
            city = canonicalize_place_name(row.get("City") or "") or polish_title(row.get("City") or "")
            details = (row.get("Activity details") or "").strip()
            if not details:
                continue
            title = _title_from_details(city, details)
            if not title:
                continue
            entries.append(
                ActivityTrainingEntry(
                    city=city,
                    title=title,
                    time=_field_from_details(details, "Time"),
                    meeting_point=_field_from_details(details, "Meeting point"),
                    inclusions=_split_inclusions(_field_from_details(details, "Inclusions")),
                    description=_field_from_details(details, "Description"),
                    source_line=details,
                )
            )
    return tuple(entries)


def match_activity_training_entry(
    source: str,
    *,
    city: str = "",
    source_title: str = "",
    min_score: float = 0.72,
) -> ActivityTrainingEntry | None:
    """Return a high-confidence catalogue entry for a supplier activity.

    Matching is deliberately conservative.  City must agree when both sides know
    it, and title-token overlap must be high unless the canonical title appears
    as a direct substring.  This lets the catalogue improve known products while
    avoiding broad guesswork for genuinely new activities.
    """

    source_text = _normalize_text(" ".join(part for part in [source_title, source] if part))
    if not source_text:
        return None
    source_city = canonicalize_place_name(city or "")
    title_tokens = _tokens(source_title or source)
    source_tokens = _tokens(source_text)
    if not source_tokens:
        return None

    best: tuple[float, ActivityTrainingEntry] | None = None
    for entry in activity_training_entries():
        if source_city and entry.city and source_city.lower() != entry.city.lower():
            continue
        entry_title_norm = _normalize_text(entry.title)
        entry_tokens = _tokens(entry.title)
        if not entry_tokens:
            continue
        direct = entry_title_norm and (entry_title_norm in source_text or source_text in entry_title_norm)
        overlap = len(entry_tokens & (title_tokens or source_tokens))
        recall = overlap / max(len(entry_tokens), 1)
        precision = overlap / max(len(title_tokens or source_tokens), 1)
        score = 1.0 if direct else (0.72 * recall + 0.28 * precision)
        # Require an identity anchor so generic labels such as "round-trip ticket"
        # do not accidentally match a specific product in the same city.
        has_anchor = bool(entry_tokens & source_tokens & {"northern_lights", "base_camp", "snowmobile", "reindeer", "husky", "santa", "suomenlinna", "fløibanen", "fjord", "cruise", "walking", "korouoma", "ranua", "tallinn", "nutshell"})
        if score >= min_score and (direct or has_anchor):
            if best is None or score > best[0]:
                best = (score, entry)
    return best[1] if best else None


def catalogue_description_for_row(row: dict) -> str:
    source = " ".join(str(row.get(key, "") or "") for key in ("original_title", "title", "details", "description"))
    entry = match_activity_training_entry(source, city=str(row.get("city", "") or ""), source_title=str(row.get("original_title") or row.get("title") or ""))
    return entry.description if entry and entry.description else ""


def validate_activity_training_catalogue() -> tuple[str, ...]:
    """Return schema/data problems for the bundled activity training catalogue.

    The file is used as regression/training data, so problems should be caught
    by tests instead of surfacing later as weak product matches or poor PDF text.
    """

    errors: list[str] = []
    if not _DATA_PATH.exists():
        return (f"missing activity training catalogue: {_DATA_PATH}",)

    required = {"Activity", "City", "Activity details"}
    seen_keys: set[tuple[str, str]] = set()
    with _DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = set(reader.fieldnames or ())
        missing = sorted(required - fieldnames)
        if missing:
            return (f"activity training catalogue missing columns: {', '.join(missing)}",)
        for line_number, row in enumerate(reader, start=2):
            row_type = (row.get("Activity") or "").strip()
            if row_type.lower() != "activity":
                errors.append(f"line {line_number}: non-activity row found in activity catalogue: {row_type or 'blank'}")
                continue
            city = (row.get("City") or "").strip()
            details = (row.get("Activity details") or "").strip()
            if not city:
                errors.append(f"line {line_number}: missing city")
            if not details:
                errors.append(f"line {line_number}: missing activity details")
                continue
            title = _title_from_details(canonicalize_place_name(city) or city, details)
            if not title:
                errors.append(f"line {line_number}: could not parse activity title")
            for label in ("Time", "Meeting point", "Inclusions", "Description"):
                if f" - {label}:" not in details:
                    errors.append(f"line {line_number}: missing '- {label}:' field")
            time_key = re.sub(r"\s+", " ", _field_from_details(details, "Time").strip().lower())
            key = (_normalize_text(city), _normalize_text(title), time_key)
            if key in seen_keys:
                errors.append(f"line {line_number}: duplicate city/title/time entry: {city} / {title}")
            seen_keys.add(key)

    if not seen_keys:
        errors.append("activity training catalogue contains no activity rows")
    return tuple(errors)
