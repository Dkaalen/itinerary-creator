"""Extract and annotate optional extras declared by group-tour packages."""

import re
from copy import deepcopy
from typing import Iterable

from itinerary_domain.group_tour_detection import is_group_tour_overview
from itinerary_domain.group_tour_supplier_titles import clean_group_tour_text
from text_polish import polish_title

_LINE_RE = re.compile(r"\boptional\b\s+(.+)$", flags=re.IGNORECASE)
_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÝÞÆÖáðéíóúýþæöøåäöØÅÄÖ]+", flags=re.IGNORECASE)


def _tokens(value: str) -> set[str]:
    stop = {"optional", "tour", "entrance", "admission", "activity", "experience", "person", "per", "fee", "the", "and", "or", "at", "to", "from"}
    return {token for token in {re.sub(r"s$", "", item.lower()) for item in _TOKEN_RE.findall(str(value or ""))} if token not in stop and len(token) > 2}


def extract_optional_group_tour_extra_titles(rows: Iterable[dict]) -> list[str]:
    extras = []
    for row in rows or []:
        if not is_group_tour_overview(row): continue
        source = str(row.get("details") or row.get("original_title") or row.get("title") or ""); active = False
        for raw in source.replace("–", "-").splitlines():
            line = clean_group_tour_text(raw).strip(" •-*|:"); lower = line.lower()
            if re.match(r"^not\s+included\b", lower): active = True; continue
            if active and re.match(r"^(what\s+to\s+expect|what'?s\s+included|what’s\s+included|overview|itinerary)\b", lower): active = False; continue
            match = _LINE_RE.search(line) if active else None
            if not match: continue
            title = re.sub(r"\([^)]*(?:€|\$|£|NOK|SEK|DKK|ISK|USD|EUR|GBP|kr|/person)[^)]*\)", "", match.group(1), flags=re.IGNORECASE)
            title = re.sub(r"\b\d[\d.,]*\s*(?:€|\$|£|NOK|SEK|DKK|ISK|USD|EUR|GBP|kr)\b", "", title, flags=re.IGNORECASE)
            title = polish_title(clean_group_tour_text(title).strip(" .:-"))
            if title and title not in extras: extras.append(title)
    return extras


def annotate_group_tour_optional_extras(rows: list[dict]) -> list[dict]:
    updated = [deepcopy(row) for row in rows or []]; token_sets = [_tokens(title) for title in extract_optional_group_tour_extra_titles(updated)]; token_sets = [item for item in token_sets if item]
    for row in updated:
        if (row.get("effective_type") or row.get("type")) != "Activity": continue
        clean_title = _tokens(row.get("title", ""))
        for tokens in token_sets:
            whale = "whale" in tokens and "whale" in clean_title
            if tokens <= clean_title or whale or (len(tokens & clean_title) >= max(1, min(len(tokens), 2)) and len(clean_title) <= len(tokens) + 2):
                row["group_tour_optional_extra"] = True; row["suppress_fallback_inclusions"] = True; break
    return updated
