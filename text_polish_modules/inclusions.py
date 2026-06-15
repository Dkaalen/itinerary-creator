"""Client-facing inclusion item cleanup."""

from __future__ import annotations

import re

from text_polish_modules.text_cleanup import dedupe_or_similar, polish_client_text


def polish_inclusion_item(value: str, context_title: str = "") -> str:
    item = polish_client_text(value).strip(" •-*\t")
    lower = item.lower().strip(" :?.,")

    if not item:
        return ""

    remove_exact = {
        "what's included",
        "what’s included",
        "includes",
        "included",
        "what is included",
    }
    if lower in remove_exact:
        return ""

    broken_replacements = {
        "round-trip ferry is": "Round-trip ferry",
        "round trip ferry is": "Round-trip ferry",
    }
    if lower in broken_replacements:
        return broken_replacements[lower]

    if lower.endswith(" is") and len(item.split()) <= 5:
        item = item[:-3].strip()

    item = re.sub(
        r"\bProfessional authorised Helsinki Guide\b",
        "Professional authorised Helsinki guide",
        item,
        flags=re.IGNORECASE,
    )

    item = dedupe_or_similar(item)
    return item


def expand_compound_inclusion_item(item: str) -> list[str]:
    """Split only the supplier artifacts that commonly arrive as one bullet.

    This is intentionally conservative: normal phrases with commas, such as
    "Professional, English-speaking guide", remain together.
    """

    item = polish_inclusion_item(item)
    if not item:
        return []

    split_patterns = [
        r",\s*(?=English-speaking\b)",
        r",\s*(?=Knowledgeable\b)",
        r",\s*(?=Comfortable coach\b)",
        r",\s*(?=Northern Lights instructions\b)",
        r",\s*(?=Warm overalls\b)",
        r",\s*(?=Snacks\b)",
        r",\s*(?=Free photographs\b)",
        r",\s*(?=2-course\b)",
    ]

    parts = [item]
    for pattern in split_patterns:
        new_parts = []
        for part in parts:
            new_parts.extend(re.split(pattern, part, flags=re.IGNORECASE))
        parts = new_parts

    return [polish_inclusion_item(part) for part in parts if polish_inclusion_item(part)]


def polish_inclusion_items(items, context_title: str = "") -> list[str]:
    cleaned: list[str] = []

    for raw in items or []:
        expanded_items = expand_compound_inclusion_item(raw)
        for item in expanded_items:
            if not item:
                continue

            lower = item.lower()
            if cleaned:
                previous = cleaned[-1]
                previous_lower = previous.lower().strip(" ,")
                if lower in {"multilingual guide", "english-speaking guide", "small-group experience", "small group experience"} and previous_lower in {"knowledgeable", "personalized", "professional"}:
                    cleaned[-1] = f"{previous}, {item}"
                    continue
                if lower.startswith(("english-speaking", "multilingual", "small-group", "small group")) and previous_lower in {"knowledgeable", "personalized", "professional"}:
                    cleaned[-1] = f"{previous}, {item}"
                    continue
                if lower.startswith(("drinks", "drink")) and previous_lower in {"snacks", "snack"}:
                    cleaned[-1] = f"{previous}, {item}"
                    continue

            if item not in cleaned:
                cleaned.append(item)

    return cleaned

