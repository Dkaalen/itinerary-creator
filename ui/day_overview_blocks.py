"""Day overview block builders for itinerary HTML/UI output."""

import re

from itinerary_generation.route_formatter import format_suggested_route_items
from text_polish import polish_title
from ui.render_helpers import clean_space, esc, render_list_items

def _preserve_common_acronyms(text):
    replacements = {
        "Atv": "ATV", "Atvs": "ATVs", "Suv": "SUV", "Suvs": "SUVs",
        "Spa": "SPA", "Vat": "VAT", "Wifi": "WiFi", "Wi-fi": "Wi-Fi",
        "Dc3": "DC3", "Bbq": "BBQ",
    }
    result = str(text or "")
    for source, target in replacements.items():
        result = re.sub(rf"\b{re.escape(source)}\b", target, result)
    return result

def _client_title_case_fragment(value):
    text = clean_space(str(value or ""))
    if not text:
        return ""
    return _preserve_common_acronyms(polish_title(text))

def _polish_overview_item(value):
    item = clean_space(str(value or "")).strip(" •-*|:")
    if not item:
        return ""
    item = re.sub(r"\bPickupo\b", "Pick-up", item, flags=re.IGNORECASE)
    item = re.sub(r"\baiport\b", "airport", item, flags=re.IGNORECASE)
    item = re.sub(r"\bPick\s+Up\b", "Pick-up", item, flags=re.IGNORECASE)
    item = re.sub(r"\bOtpions\b", "Options", item, flags=re.IGNORECASE)
    item = re.sub(r"\binlcuded\b", "included", item, flags=re.IGNORECASE)
    item = re.sub(r"\bBrekafast\b", "Breakfast", item, flags=re.IGNORECASE)
    item = item.replace("/", " / ")
    item = re.sub(r"\s+", " ", item).strip()

    item = _client_title_case_fragment(item)

    # Keep a few destination/place spellings client-facing.
    item = re.sub(r"\bReykjavik\b", "Reykjavík", item)
    item = re.sub(r"\bKeflavik\b", "Keflavík", item)
    item = re.sub(r"\bVik\b", "Vík", item)
    item = re.sub(r"\bGothernburg\b", "Gothenburg", item, flags=re.IGNORECASE)
    item = re.sub(r"\bSvolaver\b", "Svolvær", item, flags=re.IGNORECASE)
    item = re.sub(r"\bTrosmø\b", "Tromsø", item, flags=re.IGNORECASE)
    item = re.sub(r"\bKerid\b", "Kerið", item)
    # Avoid title-casing small prepositions introduced by supplier shorthand.
    item = re.sub(r"\bTo\b", "to", item)
    item = re.sub(r"\bFrom\b", "from", item)
    item = re.sub(r"\bAnd\b", "and", item)
    item = re.sub(r"\bScenic Return Drive to\b", "Scenic return drive to", item)
    item = re.sub(r"\bLuxury Stay\b", "Overnight near Glacier Lagoon", item)
    item = re.sub(r"\bDiamond Beach\b", "Diamond Beach area", item)
    return polish_title(item)

def _split_day_overview_items(text):
    source = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    source = re.sub(r"\bRoute\s+Suggested\b", "", source, flags=re.IGNORECASE)
    source = source.replace("✅", "")
    items = []
    optional = []
    in_optional = False

    # Preserve real supplier bullet lines first.
    for raw_line in source.splitlines() if "\n" in source else re.split(r"\s*\|\s*", source):
        line = clean_space(raw_line).strip(" •-*|:")
        if not line:
            continue
        if line.lower().startswith("optional"):
            in_optional = True
            remainder = clean_space(re.sub(r"^optional\s*:?", "", line, flags=re.IGNORECASE))
            if remainder:
                line = remainder
            else:
                continue
        # Split compact route shorthand like "GOLDEN CIRCLE + SILFRA + KERIÐ".
        parts = [clean_space(part).strip(" •-*") for part in re.split(r"\s+\+\s+", line) if clean_space(part).strip(" •-*")]
        target = optional if in_optional else items
        for part in parts:
            part = _polish_overview_item(part)
            if part and part not in target:
                target.append(part)

    return items, optional

def _is_rental_overview(text):
    lower = str(text or "").lower()
    return any(marker in lower for marker in [
        "rental vehicle", "rental car", "rental suv", "car rental",
        "pick up rental", "pick up your rental", "pickup rental",
        "pick-up your rental", "airport car rental office",
        "deliver your rental", "return your rental", "drop vehicle",
    ])

def _build_rental_overview_block(row):
    text = str(row.get("details") or row.get("title") or "")
    lines = []
    for raw in text.replace("|", "\n").replace("✅", "").splitlines():
        line = _polish_overview_item(raw)
        if line:
            lines.append(line)

    pickup_lines = []
    examples = []
    included = []
    not_included = []
    mode = "pickup"
    for line in lines:
        lower = line.lower().strip(" :")
        inline_include = re.search(r"\bincludes?\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if inline_include:
            before = clean_space(line[:inline_include.start()]).strip(" -:|.")
            if before:
                pickup_lines.append(before)
            for part in re.split(r",|;", inline_include.group(1)):
                item = _polish_overview_item(part)
                if item and item.lower() != "cancellation fee":
                    included.append(item)
            mode = "included"
            continue
        if lower in {"included", "includes"}:
            mode = "included"
            continue
        if lower.startswith("not included"):
            mode = "not_included"
            remainder = clean_space(re.sub(r"^not included\s*: ?", "", line, flags=re.IGNORECASE))
            if remainder:
                not_included.append(remainder)
            continue
        if "option" in lower and "similar category" in lower:
            mode = "examples"
            continue
        if mode == "included":
            included.append(line)
        elif mode == "not_included":
            not_included.append(line)
        elif mode == "examples":
            examples.append(line)
        else:
            pickup_lines.append(line)

    is_dropoff = any(re.search(r"\b(?:drop\s*(?:off)?|return|deliver)\b.*\b(?:rental|vehicle|car)\b", line.lower()) or re.search(r"\b(?:rental|vehicle|car)\b.*\b(?:drop\s*(?:off)?|return|deliver)\b", line.lower()) for line in pickup_lines)
    vehicle_type = "rental SUV" if any("suv" in line.lower() for line in pickup_lines + examples) else "rental vehicle"
    first_example = examples[0] if examples else ""

    html_text = f'<div class="content-block day-overview-block rental-overview-block" data-row-id="{esc(row.get("row_id", ""))}">'

    if is_dropoff:
        html_text += '<div class="section-title">Travel Arrangements</div>'
        html_text += render_list_items(["Return your rental vehicle at the rental office or airport."])
        html_text += "</div>"
        return {"kind": "day_overview", "row_id": row.get("row_id", ""), "html": html_text}

    pickup_sentence = f"Pick up your {vehicle_type}"
    if first_example:
        pickup_sentence += f", such as a {first_example} or similar"
    else:
        pickup_sentence += " or similar"
    pickup_sentence += ", from the rental office or airport."

    included_clean = []
    for item in included:
        low = item.lower()
        if low == "automatic":
            item = "automatic transmission"
        included_clean.append(item)
    if included_clean:
        included_sentence = _join_rental_items(included_clean).capitalize() + " included."
    else:
        included_sentence = "Rental details as listed in the itinerary."

    html_text += '<div class="section-title">Rental vehicle</div>'
    html_text += render_list_items([pickup_sentence, included_sentence])
    if not_included:
        html_text += '<div class="section-title small-section">Not included</div>'
        html_text += render_list_items(not_included[:3])
    html_text += "</div>"
    return {"kind": "day_overview", "row_id": row.get("row_id", ""), "html": html_text}

def _join_rental_items(items):
    clean = [str(item).strip(" .") for item in items if str(item).strip(" .")]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + f" and {clean[-1]}"

def build_day_overview_block(row):
    text = row.get("details") or row.get("title", "")
    if _is_rental_overview(text):
        return _build_rental_overview_block(row)

    lower = str(text or "").lower()
    route_like = any(marker in lower for marker in ["route", "drive", "waterfalls", "scenic", "return drive", "golden circle", "silfra", "kerið", "kerid"])
    if route_like or "explore" in lower or "optional" in lower:
        section, items, optional = format_suggested_route_items(text)
    else:
        items, optional = _split_day_overview_items(text)
        section = "Included Today"

    html_text = f'<div class="content-block day-overview-block" data-row-id="{esc(row.get("row_id", ""))}">' 
    if items:
        html_text += f'<div class="section-title">{esc(section)}</div>'
        html_text += render_list_items(items)
    if optional:
        html_text += '<div class="section-title small-section">Optional ideas</div>'
        html_text += render_list_items(optional)
    html_text += "</div>"
    if not items and not optional:
        return None
    return {"kind": "day_overview", "row_id": row.get("row_id", ""), "html": html_text}

