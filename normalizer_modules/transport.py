"""Transport row normalization helpers."""

import re

from text_polish import polish_client_text, polish_title
from normalizer_modules.text_utils import text_blob
from itinerary_generation.transport_norway import _is_norway_in_a_nutshell_text, explicit_norway_nutshell_title, extract_norway_nutshell_route_points
from itinerary_generation.nutshell_parsing import is_source_backed_nutshell_route_package
from itinerary_generation.activity_products import fingerprint_activity
from itinerary_generation.transport_domain.routes import get_route_points_for_transport

def normalize_transport_title(row: dict) -> dict:
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
            if _is_unbranded_rail_fjord_package(full) and origin:
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


def _is_unbranded_rail_fjord_package(text: str) -> bool:
    """Return True for source-supported rail/fjord route packages without Nutshell branding."""

    lower = str(text or "").lower()
    has_flam_train = any(marker in lower for marker in ("flåm train", "flam train", "flåm railway", "flam railway"))
    has_fjord_cruise = "nærøyfjord" in lower or "naeroyfjord" in lower or "fjord cruise" in lower
    has_ticketed_route = "e-tickets" in lower or "all tickets" in lower or "luggage transfer" in lower
    return (
        has_flam_train
        and has_fjord_cruise
        and has_ticketed_route
        and "norway in a nutshell" not in lower
        and not is_source_backed_nutshell_route_package(text)
    )

def _is_rail_or_fjord_route_activity(row: dict) -> bool:
    text = text_blob(row).lower()
    product = fingerprint_activity(row)
    if product and product.canonical_family in {"bergen_guided_flam_day_tour"}:
        return False
    if _is_sightseeing_cruise_activity(text) and not any(
        marker in text
        for marker in [
            "norway in a nutshell",
            "luggage transfer",
            "flåm railway",
            "flam railway",
            "flåm train",
            "flam train",
            "train transfer",
            "bergen railway",
            "myrdal",
            "voss to",
            "gudvangen to",
        ]
    ):
        return False
    return (
        _is_norway_in_a_nutshell_text(text)
        or re.search(r"\btrain\s*[:|]", text)
        or ("flåm train" in text or "flam train" in text or "flåm railway" in text or "flam railway" in text)
        or ("nærøyfjord" in text or "naeroyfjord" in text) and ("rail" in text or "train" in text or "luggage transfer" in text)
    )

def _is_sightseeing_cruise_activity(text: str) -> bool:
    """Return True for cruise wording that is an experience, not route transport."""

    return any(
        marker in text
        for marker in [
            "northern lights cruise",
            "fjord cruise day trip",
            "private fjord cruise",
            "fjord cruise |",
            "fjord tour",
            "sightseeing cruise",
            "day cruise",
            "canal cruise",
            "archipelago cruise",
            "wildlife cruise",
            "silent electric ship",
            "cruise on the oslofjord",
            "mostraumen fjord cruise",
            "mostraumen",
            "geirangerfjord",
            "geiranger fjord",
            "trollfjord",
            "nærøyfjord sightseeing cruise",
            "naeroyfjord sightseeing cruise",
            "icebreaker cruise",
            "arctic explorer icebreaker",
            "polar explorer icebreaker",
            "finnish arctic explorer",
            "survival suits",
            "walk on the frozen sea",
            "float in icy arctic waters",
            "cruise & swim certificate",
        ]
    )


def _is_route_transfer_activity(row: dict) -> bool:
    text = text_blob(row).lower()
    if _is_sightseeing_cruise_activity(text):
        return False
    # Activity products may include return transfers as logistics. Do not turn
    # them into transport days when the product identity is a ticket/admission
    # or named attraction experience.
    if any(marker in text for marker in ["blue lagoon", "comfort ticket", "admission", "entry ticket", "return transfer"]):
        if any(marker in text for marker in ["what's included", "overview", "what to expect", "ticket", "admission", "experience"]):
            return False

    # Supplier sheets sometimes paste real route transport into the Activity
    # column without a leading "Bus:"/"Coach:" label. Keep only strongly
    # route-shaped wording here so activity products that merely use a bus or
    # coach (Northern Lights by coach, hop-on tickets, etc.) stay activities.
    if re.search(r"\b(?:train|flight|coach|bus|ferry)\s*[:|]", text):
        return True
    if re.search(r"\bcruise\s*(?!time\b)[:|]", text):
        return True
    if re.search(r"\b(?:long[-\s]*distance|panorama|panoramic)\b[^.]{0,80}\b(?:coach|bus)\b[^.]{0,80}\btransfer\b[^.]{0,120}\bfrom\b[^.]{1,120}\bto\b", text):
        return True
    if re.search(r"\b(?:coach|bus)\s+transfer\b[^.]{0,120}\bfrom\b[^.]{1,120}\bto\b", text) and "private" not in text:
        return True
    return False

