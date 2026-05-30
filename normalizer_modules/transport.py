"""Transport row normalization helpers."""

import re

from text_polish import polish_client_text, polish_title
from normalizer_modules.text_utils import text_blob

def normalize_transport_title(row: dict) -> dict:
    title = polish_title(row.get("title", ""))
    details = polish_client_text(row.get("details", ""))
    full = f"{title} {details}".lower()
    if "tallin" in full:
        row["title"] = re.sub("Tallin", "Tallinn", title, flags=re.IGNORECASE)
    if "rovaneimi" in full:
        row["title"] = re.sub("Rovaneimi", "Rovaniemi", title, flags=re.IGNORECASE)
    if row.get("type") == "Cruise" or "overnight cruise" in full:
        if "stockholm" in full:
            row["title"] = "Cruise to Stockholm"
            row["city"] = "Stockholm" if row.get("city", "").lower() in {"helsinki", ""} else row.get("city")
    return row

def _is_rail_or_fjord_route_activity(row: dict) -> bool:
    text = text_blob(row).lower()
    return (
        "norway in a nutshell" in text
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
            "fjord tour",
            "silent electric ship",
            "cruise on the oslofjord",
            "mostraumen fjord cruise",
        ]
    )


def _is_route_transfer_activity(row: dict) -> bool:
    text = text_blob(row).lower()
    if _is_sightseeing_cruise_activity(text):
        return False
    return bool(re.search(r"\b(?:train|flight|coach|bus|cruise|ferry)\s*[:|]", text))

