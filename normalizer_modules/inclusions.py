"""Inclusion normalization helpers."""

import re

from text_polish import polish_inclusion_item, polish_inclusion_items

def normalize_inclusion_value(value: str) -> str:
    item = polish_inclusion_item(value)
    item = re.sub(r"\bcomfortable\s+mini\s*bus\b", "Comfortable minibus", item, flags=re.IGNORECASE)
    item = re.sub(r"\bbest\s+aurora\s+spots\b", "Best available aurora viewing spots", item, flags=re.IGNORECASE)
    item = re.sub(r"\bexpert\s+guide\b", "Expert guide", item, flags=re.IGNORECASE)
    item = re.sub(r"\bhot\s+beverages?\s+and\s+(?:a\s+)?little\s+snack\b", "Hot beverages and a light snack", item, flags=re.IGNORECASE)
    item = re.sub(r"\bcoffee\s+and\s+waffles\s*/\s*cookies\b", "Coffee and waffles or cookies", item, flags=re.IGNORECASE)
    item = re.sub(r"\bhot\s+drinks?\s+and\s+snacks?\s+or\s+cookies\b", "Hot drinks and snacks or cookies", item, flags=re.IGNORECASE)
    item = re.sub(r"\bauthorized\s+english\s*-\s*speaker\s+guide\b", "Authorised English-speaking guide", item, flags=re.IGNORECASE)
    item = re.sub(r"\bbaby\s+seats?\s+[åa]re\s+provided\s+if\s+needed\b", "Baby seats are provided if needed", item, flags=re.IGNORECASE)
    item = re.sub(r"\bhot\s+drink\s+and\s+biscuits?\s+[åa]re\s+provided\b", "Hot drink and biscuits are provided", item, flags=re.IGNORECASE)
    item = re.sub(r"\bwarm\s+drink\s+and\s+cookies\s+[åa]re\s+included\b", "Warm drink and cookies are included", item, flags=re.IGNORECASE)
    item = re.sub(r"\bfood\s+and\s+drinks\s+[å]re\b", "Food and drinks are included", item, flags=re.IGNORECASE)
    item = re.sub(r"\bfood\s+and\s+drinks\s+are\b(?!\s+included)", "Food and drinks are included", item, flags=re.IGNORECASE)
    item = re.sub(r"\bwarm\s+drinks?\s*&\s*light\s+snacks?\s*/\s*sausage\b", "Warm drinks and light snacks or sausage", item, flags=re.IGNORECASE)
    item = re.sub(r"\bsnacks?\s*&\s*hot\s+drinks?\b", "Snacks and hot drinks", item, flags=re.IGNORECASE)
    item = re.sub(r"\blegends?\s*&\s*explanation\b", "legends and explanations", item, flags=re.IGNORECASE)
    item = re.sub(r"\bMagic scenery and Lapland magic\b", "Scenic Lapland wilderness experience", item, flags=re.IGNORECASE)
    item = re.sub(r"\bHotel Pick-up/drop-off\b", "Hotel pick-up/drop-off", item, flags=re.IGNORECASE)
    item = re.sub(r"\bTour guiding\b", "Local guide service", item, flags=re.IGNORECASE)
    item = re.sub(r"\bTour transportation\b", "Transport during the tour", item, flags=re.IGNORECASE)
    item = re.sub(r'^Include\s*[,":]?\s*', "", item, flags=re.IGNORECASE)
    if re.fullmatch(r"Overalls", item, flags=re.IGNORECASE):
        item = "Winter equipment provided"
    item = re.sub(r"\bThermal\s+Winter\s+overalls\b", "Thermal overalls", item, flags=re.IGNORECASE)
    item = re.sub(r"\bWinter clothes\s*\(Winter overalls and boots\)", "Winter clothes (overalls and boots)", item, flags=re.IGNORECASE)
    item = re.sub(r"\bTransfer from and to\b", "Transfer to and from", item, flags=re.IGNORECASE)
    item = re.sub(r"\bboots\b", "boots", item, flags=re.IGNORECASE)
    item = re.sub(r"\bgloves\b", "gloves", item, flags=re.IGNORECASE)
    item = re.sub(r"\bbalaclava\s*&\s*helmet\b", "balaclava and helmet", item, flags=re.IGNORECASE)
    item = re.sub(r"\bWinter equipment\b", "Winter equipment", item, flags=re.IGNORECASE)
    item = re.sub(r"\bComfortable coach transport with toilet\b", "Comfortable coach transport with onboard toilet", item, flags=re.IGNORECASE)
    item = re.sub(r"\bNorthern Lights instructions video on coach\b", "Northern Lights briefing on board", item, flags=re.IGNORECASE)
    item = re.sub(r"\b([Hh])elp with camera settings and nature photos,\s*Small-group experience", r"Help with camera settings and nature photos, Small-group experience", item)
    item = re.sub(r"(?:\s+included){2,}$", " included", item, flags=re.IGNORECASE)
    return polish_inclusion_item(item)

def split_and_merge_inclusions(items: list[str]) -> list[str]:
    cleaned = []
    raw_items = [normalize_inclusion_value(item) for item in items or [] if normalize_inclusion_value(item)]
    index = 0
    while index < len(raw_items):
        item = re.split(r"\s+-\s+(?:Description|Overview)\s*:", raw_items[index], maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:")
        if not item:
            index += 1
            continue
        lower = item.lower().strip(" ,.:")
        next_item = raw_items[index + 1] if index + 1 < len(raw_items) else ""
        next_lower = next_item.lower().strip(" ,.:")

        if lower == "authorized" and next_lower in {"english-speaker guide", "english-speaking guide", "english speaker guide"}:
            cleaned.append("Authorized English-speaking guide")
            index += 2
            continue
        if lower == "english" and next_lower in {"french speaking guide", "french-speaking guide"}:
            cleaned.append("English- and French-speaking guide")
            index += 2
            continue
        if lower in {"winter overalls", "winter equipment provided"} and next_lower == "boots":
            following = [raw_items[i].lower().strip(" ,.:&") for i in range(index + 2, min(index + 5, len(raw_items)))]
            if "gloves" in following or any("balaclava" in value for value in following):
                cleaned.append("Winter equipment provided")
                index += 1
                while index < len(raw_items) and raw_items[index].lower().strip(" ,.:&") in {"boots", "gloves", "balaclava and helmet"}:
                    index += 1
                continue
        if lower == "stories" and next_lower in {"legends and explanations", "legends & explanation"}:
            cleaned.append("Stories, legends and explanations")
            index += 2
            continue

        # Split a common comma-merged bullet from photo-tour rows.
        if ", small-group experience" in lower:
            first, second = re.split(r",\s*(?=Small-group experience)", item, maxsplit=1, flags=re.IGNORECASE)
            for part in [first, second]:
                part = normalize_inclusion_value(part)
                if part and part not in cleaned:
                    cleaned.append(part)
            index += 1
            continue

        if "guided hike in korouoma canyon," in lower:
            first = re.split(r",\s*(?=Small groups|small groups)", item, maxsplit=1)[0].strip()
            item = normalize_inclusion_value(first)
            lower = item.lower().strip(" ,.:")

        if lower in {"small groups", "small groups (max 8 guests)", "max 8 guests"}:
            index += 1
            continue

        if item and item not in cleaned:
            cleaned.append(item)
        index += 1

    return polish_inclusion_items(cleaned)

