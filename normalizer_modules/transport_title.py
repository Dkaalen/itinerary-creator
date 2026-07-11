"""Transport title normalization."""

from __future__ import annotations

import re

from itinerary_domain.activity_products import fingerprint_activity
from itinerary_generation.transport_domain.routes import get_route_points_for_transport
from itinerary_domain.transport_norway import (
    _is_norway_in_a_nutshell_text,
    explicit_norway_nutshell_title,
    extract_norway_nutshell_route_points,
)
from normalizer_modules.transport_rail_fjord import is_unbranded_rail_fjord_package
from text_polish import polish_client_text, polish_title


def normalize_transport_title(row: dict) -> dict:
    """Normalize one transport row title without changing row classification."""

    title = polish_title(row.get("title", ""))
    details = polish_client_text(row.get("details", ""))
    original_title = polish_client_text(row.get("original_title", ""))
    full = f"{original_title} {title} {details}".lower()
    product = fingerprint_activity(row)
    if product and product.display_title and (
        product.product_type not in {"scenic_route"}
        or product.canonical_family == "norway_in_a_nutshell"
    ):
        row["title"] = product.display_title
        row["activity_product"] = product.as_row_metadata
        if product.route_legs:
            row["route_legs"] = [dict(leg) for leg in product.route_legs]
        return row
    if "tallin" in full:
        row["title"] = re.sub("Tallin", "Tallinn", title, flags=re.IGNORECASE)
    if "rovaneimi" in full:
        row["title"] = re.sub("Rovaneimi", "Rovaniemi", title, flags=re.IGNORECASE)

    row_type = str(row.get("effective_type") or row.get("type") or "")
    if row_type == "Transfer":
        city = polish_title(row.get("city", ""))
        if re.search(r"\bhotel\s+to\s+arctic\s+snow\s*hotel\b", full, flags=re.IGNORECASE):
            row["title"] = "Transfer from your hotel to Arctic SnowHotel"
        elif re.search(r"\b(?:arctic\s+)?snow\s*hotel\s+to\s+(?:railway\s+)?station\b", full, flags=re.IGNORECASE):
            destination = f"{city} Railway Station" if city else "the railway station"
            row["title"] = f"Transfer from Arctic SnowHotel to {destination}"
        elif re.search(r"\bprivate\s+(?:transfer\s+)?(?:railway\s+)?station\s+to\s+(?:the\s+)?airport\b", full, flags=re.IGNORECASE):
            station = f"{city} Railway Station" if city else "the railway station"
            airport = f"{city} Airport" if city else "the airport"
            row["title"] = f"Private transfer from {station} to {airport}"

    if row_type == "Train" and not _is_norway_in_a_nutshell_text(full):
        origin, destination = get_route_points_for_transport(row)
        if origin:
            row["route_origin"] = origin
        if destination:
            row["route_destination"] = destination
            if is_unbranded_rail_fjord_package(full) and origin:
                row["title"] = f"Scenic Rail & Fjord Journey from {origin} to {destination}"
            elif "santa claus express" in full:
                row["title"] = f"Santa Claus Express to {destination}"
            elif re.search(r"\b(?:overnight|night\s+train|sleeper|sleeping)\b", full):
                row["title"] = f"Overnight Train to {destination}"
            else:
                row["title"] = f"Train to {destination}"
    if _is_norway_in_a_nutshell_text(full):
        product = fingerprint_activity(row)
        if product and product.display_title:
            row["title"] = product.display_title
            row["activity_product"] = product.as_row_metadata
            if product.route_legs:
                row["route_legs"] = [dict(leg) for leg in product.route_legs]
        else:
            source_text = f"{row.get('original_title', '')} {row.get('title', '')} {row.get('details', '')}"
            explicit_title = explicit_norway_nutshell_title(source_text)
            if explicit_title:
                row["title"] = explicit_title
            else:
                points = extract_norway_nutshell_route_points(source_text)
                destination = points[-1] if points else row.get("city", "")
                row["title"] = f"Norway in a Nutshell to {polish_title(destination)}" if destination else "Norway in a Nutshell"
    if row.get("type") == "Cruise" or "overnight cruise" in full:
        if "stockholm" in full:
            row["title"] = "Cruise to Stockholm"
            row["city"] = "Stockholm" if row.get("city", "").lower() in {"helsinki", ""} else row.get("city")
    return row


__all__ = ["normalize_transport_title"]
