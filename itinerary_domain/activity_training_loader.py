"""Load and parse bundled activity-training catalogue rows."""

import csv
from functools import lru_cache
from pathlib import Path
from itinerary_domain.activity_training_model import ActivityTrainingEntry
from itinerary_domain.activity_training_text import field_from_details,split_inclusions,title_from_details
from place_aliases import canonicalize_place_name
from text_polish import polish_title

DATA_PATH=Path(__file__).resolve().parent/"data"/"activity_training_master_3col.tsv"

@lru_cache(maxsize=1)
def activity_training_entries()->tuple[ActivityTrainingEntry,...]:
    if not DATA_PATH.exists():return ()
    entries=[]
    with DATA_PATH.open("r",encoding="utf-8-sig",newline="") as handle:
        for row in csv.DictReader(handle,delimiter="\t"):
            if (row.get("Activity") or "").strip().lower()!="activity":continue
            city=canonicalize_place_name(row.get("City") or "") or polish_title(row.get("City") or "");details=(row.get("Activity details") or "").strip();title=title_from_details(city,details) if details else ""
            if title:entries.append(ActivityTrainingEntry(city,title,field_from_details(details,"Time"),field_from_details(details,"Meeting point"),split_inclusions(field_from_details(details,"Inclusions")),field_from_details(details,"Description"),details))
    return tuple(entries)
