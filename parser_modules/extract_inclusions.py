"""Inclusion and luggage extraction helpers for supplier activity text."""

from __future__ import annotations

import re

from parser_modules.common import clean_space, polish_inclusion_items
from parser_modules.details import extract_between_markers, extract_detail, split_comma_list


def _extract_norway_in_a_nutshell_includes(text: str) -> list[str]:
    lower_full = text.lower()
    if "norway in a nutshell" not in lower_full:
        return []

    includes = [
        "Bergen Railway",
        "Flåm Railway",
        "Fjord cruise",
        "Scenic bus journey",
    ]
    if "luggage porter" in lower_full:
        includes.append("Luggage porter service")
    return includes


def _merge_compound_gear_items(items: list[str]) -> list[str]:
    """Repair common comma splits inside winter clothing phrases."""

    merged: list[str] = []
    for item in items:
        lower = item.lower().strip()
        if (
            merged
            and lower in {"boots and gloves", "boots & gloves"}
            and any(marker in merged[-1].lower() for marker in ["overalls", "thermal suit", "winter clothing"])
        ):
            merged[-1] = f"{merged[-1]}, {item}"
            continue
        merged.append(item)
    return merged


def _split_pipe_inclusion_candidates(main_text: str) -> list[str]:
    # Some colleague/supplier rows use pipe sections without a formal
    # "What's included?" label, for example:
    # Title | 10 AM | 4 Hrs | guide, pickup, lunch | Pick up / meeting point ...
    # Treat the post-duration pipe section as inclusions when it looks like a
    # short inclusion list, but stop before any formal meeting-point section.
    pipe_parts = [clean_space(part) for part in main_text.split("|")]
    if len(pipe_parts) < 3:
        return []

    pipe_candidates: list[str] = []
    for part in pipe_parts[2:]:
        lower_part = part.lower()
        if any(marker in lower_part for marker in ["overview", "what to expect", "not included"]):
            continue
        part = re.split(
            r"pick[-\s]*up\s*/\s*meeting\s*point|pickup\s*/\s*meeting\s*point|meeting\s*point\s*:",
            part,
            flags=re.IGNORECASE,
        )[0].strip(" :|-")
        part = re.sub(r"^(?:includes?|included)\s*[:,-]?\s*", "", part, flags=re.IGNORECASE).strip(" :|-")
        if not part or len(part) > 450:
            continue

        lower_part = part.lower()
        inclusion_markers = [
            "included",
            "ticket",
            "pick-up",
            "pickup",
            "drop-off",
            "lunch",
            "certificate",
            "transport",
            "guide",
            "meal",
            "snack",
            "drink",
            "photograph",
            "camera",
            "tax",
            "overalls",
            "tripod",
            "ferry",
            "equipment",
            "berry juice",
            "hot berry",
            "winter",
            "admission",
            "entry",
            "access",
            "ritual",
            "mask",
            "towel",
            "bathrobe",
            "locker",
            "boat",
            "snacks",
        ]
        prose_markers = [
            "tour gives",
            "take a stroll",
            "listen to",
            "make sense",
            "to top it all",
            "waterworld",
            "best way to understand",
        ]
        marker_hits = sum(1 for marker in inclusion_markers if marker in lower_part)
        looks_like_prose = any(marker in lower_part for marker in prose_markers)
        looks_like_list = (part.count(",") >= 1 or marker_hits >= 2) and not looks_like_prose
        if looks_like_list:
            pipe_candidates.extend(split_comma_list(part, protect_compound_phrases=True))

    return _merge_compound_gear_items(polish_inclusion_items(pipe_candidates)) if pipe_candidates else []


def extract_includes_from_description(main_text: str) -> list[str]:
    """Extract included services/items from supplier activity text."""

    main_text = str(main_text or "")
    lower_full = main_text.lower()

    nutshell_includes = _extract_norway_in_a_nutshell_includes(main_text)
    if nutshell_includes:
        return nutshell_includes

    standard_includes = extract_detail(main_text, "Includes")

    if standard_includes:
        return _merge_compound_gear_items(split_comma_list(standard_includes, protect_compound_phrases=True))

    section = extract_between_markers(
        main_text,
        [
            r"what'?s included\??",
            r"what’s included\??",
            r"\bincludes\s*:\s*",
            r"(?<!not\s)\bincluded\s*:\s*",
            r"\binclude\s*[,|:]\s*",
        ],
        [
            r"pick[-\s]*up\s*/\s*meeting\s*point",
            r"pickup\s*/\s*meeting\s*point",
            r"\bmeeting\s*point\b",
            r"\boverview\b",
            r"\bnot\s+in(?:cl|lc)uded\b",
            r"\bwhat to expect\b",
            r"\bimportant info\b",
            r"\bour floating suits\b",
            r"\byou will\b",
            r"\byou are\b",
            r"\btravel to\b",
            r"\barguably\b",
            r"\bwhen selecting\b",
            r"\bafter having\b",
            r"\bdo not worry\b",
        ],
    )

    if section:
        return _merge_compound_gear_items(split_comma_list(section, protect_compound_phrases=True))

    pipe_candidates = _split_pipe_inclusion_candidates(main_text)
    if pipe_candidates:
        return pipe_candidates

    fallback_includes: list[str] = []

    if "ticket" in lower_full and "included" in lower_full:
        fallback_includes.append("Tickets included")

    if "luggage porter" in lower_full:
        fallback_includes.append("Luggage porter service included")

    return fallback_includes


def extract_luggage_included(main_text: str) -> str:
    """Extract standalone luggage-included text when present."""

    main_text = str(main_text or "")
    luggage = extract_detail(main_text, "Luggage included")

    if luggage:
        return luggage

    if "luggage" in main_text.lower() and "included" in main_text.lower():
        for part in re.split(r"[-|]", main_text):
            if "luggage" in part.lower() and "included" in part.lower():
                return clean_space(part)

    return ""


__all__ = ["extract_includes_from_description", "extract_luggage_included"]
