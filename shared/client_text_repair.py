"""Shared client-facing text repair helpers.

The normalizer and transport generation layers both need the same conservative
supplier-typo repairs.  Keeping this source-free helper outside generation
prevents parser/normalizer code from importing render/copy modules.
"""

from __future__ import annotations

import re

from shared.text_cleanup_rules import apply_case_replacements, apply_common_text_replacements

COMMON_TEXT_REWRITES: tuple[tuple[str, str], ...] = (
    (r"\btranfers\b|\btrasfer\b|\btransffer\b|\btranfer\b", "transfers"),
    (r"\btrnasfer\b|\btrasnfer\b", "transfer"),
    (r"\brelased\b|\brelesed\b", "released"),
    (r"\bbrekafast\b|\bbreakfest\b", "breakfast"),
    (r"\baccomodation\b|\baccommondation\b", "accommodation"),
    (r"\bfunicual\b", "funicular"),
    (r"\bprofesional\b", "professional"),
    (r"\bquadrouple\b", "quadruple"),
    (r"\bdoubel\b", "double"),
    (r"\bcenrally\b", "centrally"),
    (r"\bofficie\b|\boffcie\b", "office"),
    (r"\bluggaes\b|\bluagges\b|\bluggages\b", "luggage"),
    (r"\bmilage\b", "mileage"),
    (r"\bFight\s*:", "Flight:"),
    (r"\bDate\s+dependant\b|\bDate\s+dependent\b", "Timing to be confirmed"),
    (r"\b2s\s+Sitting\b", "Second class seating"),
    (r"\bsecond\s+sitting\b", "Second class seating"),
    (r"\b1change\b", "1 change"),
    (r"\bbustation\b", "Bus Station"),
)

PLACE_REWRITES: tuple[tuple[str, str], ...] = (
    (r"\bRovaneimi\b", "Rovaniemi"),
    (r"\brovaniemi\b", "Rovaniemi"),
    (r"\blevi\b", "Levi"),
    (r"\bkittila\b", "Kittilä"),
    (r"\btromso\b", "Tromsø"),
    (r"\bflam\b", "Flåm"),
    (r"\balesund\b", "Ålesund"),
    (r"\breykjavik\b", "Reykjavík"),
    (r"\bkeflavik\b", "Keflavík"),
    (r"\bhofn\b", "Höfn"),
    (r"\begilsstadir\b", "Egilsstaðir"),
    (r"\bsvolaver\b", "Svolvær"),
    (r"\bbergebn\b", "Bergen"),
)


def repair_messy_client_text(value: str) -> str:
    """Conservative typo/phrase repair for already-client-facing snippets."""

    text = str(value or "")
    if not text:
        return ""
    text = text.replace("–", "-").replace("—", "-")
    text = apply_common_text_replacements(text)
    text = apply_case_replacements(text)
    for pattern, repl in COMMON_TEXT_REWRITES:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    for pattern, repl in PLACE_REWRITES:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    text = re.sub(r"\bBus\s+station\b", "Bus Station", text, flags=re.IGNORECASE)
    text = re.sub(r"\bRail\s+Station\b|\bTrain\s+Station\b", "Railway Station", text, flags=re.IGNORECASE)
    if "\n" in text:
        text = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text)
    else:
        text = re.sub(r"\s+", " ", text)
    return text.strip()


__all__ = ["COMMON_TEXT_REWRITES", "PLACE_REWRITES", "repair_messy_client_text"]
