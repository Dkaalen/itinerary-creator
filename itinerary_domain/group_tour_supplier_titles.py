"""Extract supplier day numbers and headings for group tours."""

import re

from text_polish import polish_title


def clean_group_tour_text(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def day_number(value: str) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def _trim_title(value: str) -> str:
    title = clean_group_tour_text(value).strip(" .:-|")
    title = re.split(r"\s+(?=We\s|You\s|The\s|A\s+\d|Prepare\s|Once\s|After\s|At\s|On\s)", title, maxsplit=1)[0].strip(" .:-|")
    return re.sub(r"\bJökulsárlón\s*&\s*Ice Caves\b", "Jökulsárlón Glacier Lagoon & Ice Caves", title, flags=re.IGNORECASE)


def extract_supplier_day_title(text: str) -> str:
    source = str(text or "").strip()
    for line in source.splitlines() or [source]:
        match = re.search(r"^\s*Day\s*\d+\s*:\s*([^|]+)", line, flags=re.IGNORECASE)
        if match and _trim_title(match.group(1)): return polish_title(re.sub(r"\s+&\s+", " & ", _trim_title(match.group(1))))
    match = re.search(r"(?:^|\n|\|)\s*Day\s*\d+\s*:\s*([^\n|]+)", source, flags=re.IGNORECASE)
    return polish_title(re.sub(r"\s+&\s+", " & ", _trim_title(match.group(1)))) if match else ""


def supplier_day_number(row: dict) -> int:
    text = f'{row.get("original_title", "")}\n{row.get("details", "")}\n{row.get("title", "")}'
    match = re.search(r"(?:^|\n|\|)\s*Day\s*(\d+)\s*:", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else 0
