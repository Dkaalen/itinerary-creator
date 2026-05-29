"""Shared parser text cleanup helpers."""

import re

import diagnostics
from place_aliases import normalize_place_text
from text_polish import polish_client_text


def clean_space(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


COMMON_TEXT_REPLACEMENTS = [
    (r"\bNUtshell\b", "Nutshell"),
    (r"\bFLybus\b", "Flybus"),
    (r"\bFlyBus\b", "Flybus"),
    (r"\bReykajvik\b", "Reykjavík"),
    (r"\bReykavik\b", "Reykjavík"),
    (r"\bCity Centre\b", "city centre"),
    (r"\bStaion\b", "Station"),
    (r"\bNutsheel\b", "Nutshell"),
    (r"\bNorway\s+in\s+a\s+Nutshell\b", "Norway in a Nutshell"),
    (r"\bBrekafast\b", "Breakfast"),
    (r"\bOverngiht\b", "Overnight"),
    (r"\bBrekfast\b", "Breakfast"),
    (r"\bDoubel\b", "Double"),
    (r"\bArrnaged\b", "arranged"),
    (r"\binclueded\b", "included"),
    (r"\binclued\b", "included"),
    (r"\bBergent\b", "Bergen"),
    (r"\bSvolaver\b", "Svolvær"),
    (r"\bSVolaver\b", "Svolvær"),
    (r"\bSvolvaer\b", "Svolvær"),
    (r"\bSvoalvaer\b", "Svolvær"),
    (r"\bTrosmø\b", "Tromsø"),
    (r"\bTrosmo\b", "Tromsø"),
    (r"\bGothernburg\b", "Gothenburg"),
    (r"\bGothenbrug\b", "Gothenburg"),
    (r"\baccommodaiton\b", "accommodation"),
    (r"\binlcuded\b", "included"),
    (r"\bInlcuded\b", "Included"),
    (r"\bIncludse\b", "Includes"),
    (r"\bFull\s+Pention\b", "Full pension"),
    (r"\bFull\s+Pension\b", "Full pension"),
    (r"\bOptinal\b", "Optional"),
    (r"\bRecepion\b", "Reception"),
    (r"\bStaion\b", "Station"),
    (r"\bKriuna\b", "Kiruna"),
    (r"\bwitj\b", "with"),
    (r"\bTromso\b", "Tromsø"),
    (r"\bKakslauttenen\b", "Kakslauttanen"),
    (r"\b(\d{1,2})\s+:\s*(\d{2})", r"\1:\2"),
    (r"\bWi-FI\b", "Wi-Fi"),
    (r"\bPickupo\b", "Pick up"),
    (r"\bOtpions\b", "Options"),
    (r"\bticktes\b", "tickets"),
    (r"\bROute\b", "Route"),
    (r"\binlc\b", "incl"),
    (r"\b4Star\b", "4 Star"),
    (r"\b3Star\b", "3 Star"),
]

SUSPICIOUS_FRAGMENTS = [
    "brekafast",
    "brekfast",
    "arrnaged",
    "inclueded",
    "inclued",
    "doubel",
    "bergent",
    "svolaver",
    "svoalvaer",
    "nutsheel",
    "nutshel",
]


def fix_common_text(value):
    """Silently fixes small recurring spelling/capitalization issues in pasted itineraries."""

    text = str(value or "")

    for pattern, replacement in COMMON_TEXT_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = normalize_place_text(text)
    text = polish_client_text(text)

    return clean_space(text) if "\n" not in text else text


def check_for_unknown_typos(text, context=""):
    """Warn if known suspicious fragments remain after normal cleanup."""

    lower = str(text or "").lower()

    for fragment in SUSPICIOUS_FRAGMENTS:
        if fragment in lower:
            diagnostics.warn(
                "possible_typo",
                f"Possible uncorrected typo '{fragment}' found after text cleaning" + (f" in {context}" if context else ""),
                raw_value=str(text or "")[:200],
            )
