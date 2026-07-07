"""Regex rules for client-facing text cleanup.

This module owns the large replacement tables so ``text_cleanup`` can focus on
cleanup orchestration rather than becoming a rule dump.
"""

from __future__ import annotations

import re

# One maintainable pass for itinerary proper nouns and activity phrases.
# This prevents half-cased client-facing output such as "south Coast" or
# "whale Watching" without adding one-off patches at each rendering site.
PROPER_NOUN_REPLACEMENTS = [
    (r"\bsouth\s+coast\b", "South Coast"),
    (r"\bnorth\s+iceland\b", "North Iceland"),
    (r"\beast\s+iceland\b", "East Iceland"),
    (r"\beastfjords\b", "Eastfjords"),
    (r"\bwestfjords\b", "Westfjords"),
    (r"\bwest\s+iceland\b", "West Iceland"),
    (r"\bsn[æa]fellsnes\b", "Snæfellsnes"),
    (r"\bborgarfj[oö]r[dð]ur\b", "Borgarfjörður"),
    (r"\bhallormssta[ðd]ask[oó]gar\b", "Hallormsstaðaskógar"),
    (r"\blagaflj[oó]t\b", "Lagafljót"),
    (r"\bm[yý]vatn\b", "Mývatn"),
    (r"\bn[áa]mskar[ðd]\b", "Námskarð"),
    (r"\bdettifoss\b", "Dettifoss"),
    (r"\bgo[ðd]afoss\b", "Goðafoss"),
    (r"\bhauganes\b", "Hauganes"),
    (r"\bskaftafell\b", "Skaftafell"),
    (r"\bkatla\b", "Katla"),
    (r"\bvatnaj[oö]kull\b", "Vatnajökull"),
    (r"\bj[oö]kuls[áa]rl[oó]n\b", "Jökulsárlón"),
    (r"\bblue\s+ice\s+cave\b", "Blue Ice Cave"),
    (r"\bdiamond\s+beach\b", "Diamond Beach"),
    (r"\bwhale\s+watching\b", "Whale Watching"),
    (r"\bice\s+cave\b", "Ice Cave"),
    (r"\bglacier\s+lagoon\b", "Glacier Lagoon"),
    (r"\bfjellheisen\b", "Fjellheisen"),
]

CASE_REPLACEMENTS = [
    (r"\bHScandic\b", "Scandic"),
    (r"\bMArina\b", "Marina"),
    (r"\bGrand\s+MArina\b", "Grand Marina"),
    (r"\bFunicual\b", "Funicular"),
    (r"\bFunicualr\b", "Funicular"),
    (r"\bComfort\s+hotel\b", "Comfort Hotel"),
    (r"\bquality\s+grand\b", "Quality Grand"),
    (r"\bscandic\b", "Scandic"),
    (r"\bthon\s+hotel\b", "Thon Hotel"),
    (r"\bhotel\s+mayfair\b", "Hotel Mayfair"),
    (r"\bsanta's\s+hotel\b", "Santa's Hotel"),
    (r"\bstandard\s+doubel\s+room\b", "Standard Double Room"),
    (r"\bstandard\s+double\s+room\b", "Standard Double Room"),
    (r"\bstandard\s+room\b", "Standard Room"),
]


COMPILED_CASE_REPLACEMENTS = tuple(
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in (*CASE_REPLACEMENTS, *PROPER_NOUN_REPLACEMENTS)
)


def apply_case_replacements(text: str) -> str:
    for pattern, replacement in COMPILED_CASE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


__all__ = [
    "CASE_REPLACEMENTS",
    "PROPER_NOUN_REPLACEMENTS",
    "COMPILED_CASE_REPLACEMENTS",
    "apply_case_replacements",
]
