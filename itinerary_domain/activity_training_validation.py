"""Validate schema and uniqueness of bundled activity-training data."""

import csv,re
from itinerary_domain.activity_training_loader import DATA_PATH
from itinerary_domain.activity_training_text import field_from_details,normalize_training_text,title_from_details
from place_aliases import canonicalize_place_name

def validate_activity_training_catalogue()->tuple[str,...]:
    if not DATA_PATH.exists():return (f"missing activity training catalogue: {DATA_PATH}",)
    errors=[];seen=set();required={"Activity","City","Activity details"}
    with DATA_PATH.open("r",encoding="utf-8-sig",newline="") as handle:
        reader=csv.DictReader(handle,delimiter="\t");missing=sorted(required-set(reader.fieldnames or ()))
        if missing:return (f"activity training catalogue missing columns: {', '.join(missing)}",)
        for number,row in enumerate(reader,start=2):
            kind=(row.get("Activity") or "").strip();city=(row.get("City") or "").strip();details=(row.get("Activity details") or "").strip()
            if kind.lower()!="activity":errors.append(f"line {number}: non-activity row found in activity catalogue: {kind or 'blank'}");continue
            if not city:errors.append(f"line {number}: missing city")
            if not details:errors.append(f"line {number}: missing activity details");continue
            title=title_from_details(canonicalize_place_name(city) or city,details)
            if not title:errors.append(f"line {number}: could not parse activity title")
            for label in ("Time","Meeting point","Inclusions","Description"):
                if f" - {label}:" not in details:errors.append(f"line {number}: missing '- {label}:' field")
            key=(normalize_training_text(city),normalize_training_text(title),re.sub(r"\s+"," ",field_from_details(details,"Time").strip().lower()))
            if key in seen:errors.append(f"line {number}: duplicate city/title/time entry: {city} / {title}")
            seen.add(key)
    if not seen:errors.append("activity training catalogue contains no activity rows")
    return tuple(errors)
