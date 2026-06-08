"""Transport row normalization helpers."""

import re

from text_polish import polish_client_text, polish_title
from normalizer_modules.text_utils import text_blob
from itinerary_generation.transport_norway import _is_norway_in_a_nutshell_text, extract_norway_nutshell_route_points
from itinerary_generation.activity_products import fingerprint_activity

def normalize_transport_title(row: dict) -> dict:
    title = polish_title(row.get("title", ""))
    details = polish_client_text(row.get("details", ""))
    full = f"{title} {details}".lower()
    product = fingerprint_activity(row)
    if product and product.display_title and product.product_type not in {"scenic_route"}:
        row["title"] = product.display_title
        row["activity_product"] = product.as_row_metadata
        if product.route_legs:
            row["route_legs"] = [dict(leg) for leg in product.route_legs]
        return row
    if "tallin" in full:
        row["title"] = re.sub("Tallin", "Tallinn", title, flags=re.IGNORECASE)
    if "rovaneimi" in full:
        row["title"] = re.sub("Rovaneimi", "Rovaniemi", title, flags=re.IGNORECASE)
    if _is_norway_in_a_nutshell_text(full):
        product = fingerprint_activity(row)
        if product and product.display_title:
            row["title"] = product.display_title
            row["activity_product"] = product.as_row_metadata
            if product.route_legs:
                row["route_legs"] = [dict(leg) for leg in product.route_legs]
        else:
            points = extract_norway_nutshell_route_points(f"{row.get('title', '')} {row.get('details', '')} {row.get('original_title', '')}")
            destination = points[-1] if points else row.get("city", "")
            row["title"] = f"Norway in a Nutshell to {polish_title(destination)}" if destination else "Norway in a Nutshell"
    if row.get("type") == "Cruise" or "overnight cruise" in full:
        if "stockholm" in full:
            row["title"] = "Cruise to Stockholm"
            row["city"] = "Stockholm" if row.get("city", "").lower() in {"helsinki", ""} else row.get("city")
    return row

def _is_rail_or_fjord_route_activity(row: dict) -> bool:
    text = text_blob(row).lower()
    product = fingerprint_activity(row)
    if product and product.canonical_family in {"bergen_guided_flam_day_tour"}:
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
            "silent electric ship",
            "cruise on the oslofjord",
            "mostraumen fjord cruise",
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

