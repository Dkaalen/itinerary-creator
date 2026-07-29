"""Destination request and manifest resolution for remote image packs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from place_aliases import canonicalize_place_name, country_for_place, is_likely_service_text
from images.remote_distribution_config import normalise_lookup
from images.remote_distribution_models import DestinationRequest, DistributionError, ResolvedDestinationPack


NUTSHELL_DESTINATION = "Norway in a Nutshell"
NUTSHELL_COUNTRY = "Norway"
NUTSHELL_LOOKUP = normalise_lookup(NUTSHELL_DESTINATION)


def coerce_request(value: Any) -> DestinationRequest | None:
    if isinstance(value, DestinationRequest):
        destination = value.destination
        country = value.country
    elif isinstance(value, Mapping):
        destination = value.get("destination") or value.get("city") or value.get("location") or ""
        country = value.get("country") or ""
    else:
        destination = value
        country = ""

    destination = canonicalize_place_name(str(destination or "").strip())
    if not destination or is_likely_service_text(destination):
        return None
    country = canonicalize_place_name(str(country or "").strip()) or country_for_place(destination)
    return DestinationRequest(destination=destination, country=str(country or "").strip())



def _row_type(value: Mapping[str, Any]) -> str:
    return str(value.get("effective_type") or value.get("type") or "").strip().casefold()


def _row_city(value: Mapping[str, Any]) -> str:
    return str(value.get("city") or value.get("destination") or value.get("location") or "").strip()


def _rows_require_nutshell_pack(rows: Sequence[Mapping[str, Any]]) -> bool:
    """Return whether the dedicated Norway in a Nutshell image pack is required."""

    searchable_fields = (
        "city",
        "destination",
        "location",
        "title",
        "original_title",
        "details",
        "description",
        "display_description",
        "service_label",
        "includes",
    )
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        text = normalise_lookup(" ".join(str(row.get(field) or "") for field in searchable_fields))
        if NUTSHELL_LOOKUP in text:
            return True
    return False


def _destination_from_rows_for_pack_request(rows: Sequence[Mapping[str, Any]]) -> str:
    """Return the stay/page destination used for remote image-pack readiness.

    Image matching may consider service text such as rail segments and fjord
    route stops, but the image-bank connection gate should only request packs
    for actual itinerary page/stay destinations.  This keeps Norway in a
    Nutshell stops such as Myrdal or Gudvangen from blocking Add Pictures.
    """

    rows = [row for row in rows or [] if isinstance(row, Mapping)]
    priority_groups = (
        {"hotel", "accommodation", "lodging"},
        {"day overview"},
        {"arrival", "departure", "leisure"},
        {"activity"},
        {"train", "flight", "cruise", "ferry", "coach", "transport", "transfer", "drive", "car"},
    )
    for group in priority_groups:
        for row in rows:
            if _row_type(row) in group and _row_city(row):
                return _row_city(row)
    return next((_row_city(row) for row in rows if _row_city(row)), "")

def destination_requests_from_rows(rows_or_grouped_days: Any) -> list[DestinationRequest]:
    """Return ordered, unique day-image destinations."""

    grouped_items: list[tuple[str, list[dict[str, Any]]]] = []
    direct_values: list[Any] = []

    if isinstance(rows_or_grouped_days, Mapping):
        if any(key in rows_or_grouped_days for key in ("city", "destination", "location")):
            direct_values = [rows_or_grouped_days]
        else:
            for day, value in rows_or_grouped_days.items():
                if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                    grouped_items.append((str(day), [dict(row) for row in value if isinstance(row, Mapping)]))
    elif isinstance(rows_or_grouped_days, Sequence) and not isinstance(rows_or_grouped_days, (str, bytes, bytearray)):
        values = list(rows_or_grouped_days)
        if values and all(isinstance(value, DestinationRequest) for value in values):
            direct_values = values
        elif any(isinstance(value, Mapping) and value.get("day") for value in values):
            grouped: dict[str, list[dict[str, Any]]] = {}
            for value in values:
                if not isinstance(value, Mapping):
                    continue
                day = str(value.get("day") or "").strip() or "Day"
                grouped.setdefault(day, []).append(dict(value))
            grouped_items = list(grouped.items())
        else:
            direct_values = values
    else:
        direct_values = [rows_or_grouped_days]

    if grouped_items:
        for _day, rows in grouped_items:
            city = _destination_from_rows_for_pack_request(rows)
            if city:
                direct_values.append({"destination": city, "country": country_for_place(city)})

    specialty_rows = [
        row
        for _day, rows in grouped_items
        for row in rows
    ]
    specialty_rows.extend(value for value in direct_values if isinstance(value, Mapping))
    if _rows_require_nutshell_pack(specialty_rows):
        direct_values.append({"destination": NUTSHELL_DESTINATION, "country": NUTSHELL_COUNTRY})

    selected: list[DestinationRequest] = []
    seen: set[tuple[str, str]] = set()
    for value in direct_values:
        request = coerce_request(value)
        if request is None:
            continue
        key = (normalise_lookup(request.country), normalise_lookup(request.destination))
        if not key[1] or key in seen:
            continue
        seen.add(key)
        selected.append(request)
    return selected


def entry_aliases(entry: Mapping[str, Any], field: str) -> set[str]:
    names = {str(entry.get(field) or "")}
    aliases = entry.get(f"{field}_aliases")
    if isinstance(aliases, Sequence) and not isinstance(aliases, (str, bytes, bytearray)):
        names.update(str(value or "") for value in aliases)
    return {normalise_lookup(value) for value in names if normalise_lookup(value)}


def resolve_destination_packs(
    manifest: Mapping[str, Any],
    requests: Sequence[DestinationRequest],
) -> tuple[list[ResolvedDestinationPack], list[DestinationRequest]]:
    destinations = manifest.get("destinations") if isinstance(manifest, Mapping) else None
    if not isinstance(destinations, Mapping):
        raise DistributionError("Remote image-bank manifest has no destinations mapping.")

    entries: list[tuple[str, Mapping[str, Any], set[str], set[str]]] = []
    for manifest_key, raw_entry in destinations.items():
        if not isinstance(raw_entry, Mapping):
            continue
        entries.append((
            str(manifest_key),
            raw_entry,
            entry_aliases(raw_entry, "country"),
            entry_aliases(raw_entry, "destination"),
        ))

    resolved: list[ResolvedDestinationPack] = []
    unresolved: list[DestinationRequest] = []
    seen_assets: set[str] = set()
    for request in requests:
        destination_key = normalise_lookup(request.destination)
        country_key = normalise_lookup(request.country)
        destination_matches = [item for item in entries if destination_key in item[3]]
        if country_key:
            exact_matches = [item for item in destination_matches if country_key in item[2]]
            if exact_matches:
                destination_matches = exact_matches
        if len(destination_matches) != 1:
            unresolved.append(request)
            continue

        manifest_key, entry, _, _ = destination_matches[0]
        asset_name = str(entry.get("asset_name") or "").strip()
        download_url = str(entry.get("download_url") or "").strip()
        sha256 = str(entry.get("sha256") or "").strip().lower()
        if not asset_name or not download_url or len(sha256) != 64:
            unresolved.append(request)
            continue
        if asset_name in seen_assets:
            continue
        seen_assets.add(asset_name)
        resolved.append(ResolvedDestinationPack(
            manifest_key=manifest_key,
            country=str(entry.get("country") or "").strip(),
            destination=str(entry.get("destination") or "").strip(),
            asset_name=asset_name,
            download_url=download_url,
            sha256=sha256,
            file_count=int(entry.get("file_count") or 0),
            size_bytes=int(entry.get("size_bytes") or 0),
        ))
    return resolved, unresolved
