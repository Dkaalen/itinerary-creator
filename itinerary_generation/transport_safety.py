"""Transport output safety helpers.

Messy supplier rows are acceptable input, but raw supplier/admin wording must
not leak into client-facing preview/PDF text.  This module holds conservative
normalizers used by transport titles, day travel blocks, inclusions and
exclusions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from place_aliases import canonicalize_place_name
from text_polish import polish_client_text, polish_title


TERMINAL_SUFFIXES: tuple[tuple[str, str], ...] = (
    (r"bus\s*station|bus\s*terminal|busterminal|busstation", "Bus Station"),
    (r"coach\s*station|coach\s*terminal", "Coach Station"),
    (r"railway\s*station|train\s*station|rail\s*station|rly\s*station", "Railway Station"),
    (r"\bstation\b|\bstn\b", "Station"),
    (r"ferry\s*terminal", "Ferry Terminal"),
    (r"cruise\s*terminal", "Cruise Terminal"),
    (r"harbour|harbor", "Harbour"),
    (r"\bport\b", "Port"),
    (r"\bpier\b", "Pier"),
    (r"\bdock\b", "Dock"),
    (r"\bairport\b|\bapt\b", "Airport"),
)

_PLACE_WORD_RE = r"[A-Za-zÀ-ÿøØåÅäÄöÖæÆðÐþÞ .'-]+"

# Phrases that are useful for parsing, but should never appear raw in client
# output.  These are scanned by tests/validators and also drive fallbacks.
RAW_CLIENT_OUTPUT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("supplier_pls", r"\bpls\b|\bplz\b"),
    ("supplier_kindly", r"\bplease kindly\b|\bkindly note\b|\bplease be advised\b|\bbe informed\b"),
    ("supplier_reception", r"\brequest at reception\b|\bask reception\b|\bcontact supplier\b|\bcontact operator\b"),
    ("backend_voucher", r"\bfinal voucher\b|\bbooking voucher\b|\bservice voucher\b|\breservation reference\b|\bbooking id\b|\bsupplier ref\b"),
    ("raw_addon_cost", r"\baddon cost\b|\badd[- ]?on cost\b|\bpaid on ground\b|\bpay on spot\b|\bpayable locally\b"),
    ("raw_self_transfer_case", r"\bself Transfer\b|\bSelf Transfer\b"),
    ("transport_shorthand", r"\bPrivate Hotel to\b|\bPrivate Airport to\b|\bPrivate Station to\b|\bPrivate Bustation to\b"),
    ("supplier_future", r"\bwill be relased\b|\bwill be released\b|\bwill be advised\b|\bdetails to follow\b"),
    ("bad_transport_typo", r"\btranfers\b|\btrasfer\b|\btransffer\b|\btranfer\b|\brelased\b|\brelesed\b"),
    ("bad_flight_typo", r"\bFight\s*:"),
    ("date_dependant", r"\bdate dependant\b|\bdate dependent\b"),
    (
        "suspicious_am_pm_time_range",
        r"\b12:[0-5]\d\s*a\.?m\.?\s*[-–—]\s*(?:1[0-2]|0?[1-9]):[0-5]\d\s*p\.?m\.?\b",
    ),
)


COMMON_TEXT_REWRITES: tuple[tuple[str, str], ...] = (
    (r"\btranfers\b|\btrasfer\b|\btransffer\b|\btranfer\b", "transfers"),
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


@dataclass(frozen=True)
class ClientOutputFinding:
    code: str
    pattern: str
    excerpt: str


def _clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def repair_messy_client_text(value: str) -> str:
    """Conservative typo/phrase repair for already-client-facing snippets."""

    text = str(value or "")
    if not text:
        return ""
    text = text.replace("–", "-").replace("—", "-")
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
    return polish_client_text(text).strip()


def normalize_transport_place(value: str) -> str:
    """Normalize a place/terminal without losing useful terminal detail."""

    raw = repair_messy_client_text(value).strip(" .,-|:")
    if not raw:
        return ""
    if re.search(r"\bAirport\b", raw, flags=re.IGNORECASE) and re.search(r"\b(?:to|from)\b", raw, flags=re.IGNORECASE):
        raw = re.split(r"\b(?:to|from)\b", raw, flags=re.IGNORECASE)[-1].strip(" .,-|:")
    canonical = canonicalize_place_name(raw)
    if canonical != raw:
        return canonical

    for pattern, terminal in TERMINAL_SUFFIXES:
        match = re.search(rf"^(?P<base>{_PLACE_WORD_RE}?)\s+(?:{pattern})$", raw, flags=re.IGNORECASE)
        if match:
            base = match.group("base").strip(" .,-|:")
            base = canonicalize_place_name(repair_messy_client_text(base)) or polish_title(base)
            if not base:
                return terminal
            # Airports are usually canonical places when known.  For unknown
            # airports, keep the airport name rather than stripping it.
            return f"{base} {terminal}"

    return polish_title(raw)


def base_destination_from_terminal(value: str) -> str:
    """Return the itinerary base place for a terminal/place value.

    Example: ``Levi Bus Station`` -> ``Levi``.  Airports are preserved because
    airport names can be commercially meaningful (Kittilä Airport must not be
    rewritten as Levi Airport).
    """

    place = normalize_transport_place(value)
    if not place:
        return ""
    for pattern, terminal in TERMINAL_SUFFIXES:
        if terminal == "Airport":
            continue
        match = re.search(rf"^(?P<base>{_PLACE_WORD_RE}?)\s+(?:{pattern})$", place, flags=re.IGNORECASE)
        if match:
            base = match.group("base").strip(" .,-|:")
            return canonicalize_place_name(base) or polish_title(base)
    return canonicalize_place_name(place) or polish_title(place)


def destination_is_terminal(value: str) -> bool:
    place = normalize_transport_place(value)
    return any(
        terminal != "Airport" and place.lower().endswith(terminal.lower())
        for _, terminal in TERMINAL_SUFFIXES
    )


def clean_self_transfer_text(value: str) -> str:
    """Rewrite self-transfer supplier shorthand into client-facing wording."""

    text = repair_messy_client_text(value).strip(" .,-|:")
    if not text:
        return "Self-arranged transfer"
    text = re.sub(r"\bself[-\s]*transfer\b", "Self-arranged transfer", text, flags=re.IGNORECASE)
    text = re.sub(r"\bself[-\s]*arranged\s+transfer\b", "Self-arranged transfer", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpls\.?\s*request\s+at\s+reception\s+for\s+private\s+transfers?\s+at\s+addon\s+cost\s+to\s+be\s+paid\s+on\s+ground\b", "Private transfer may be requested locally at additional cost", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:please\s+)?request\s+at\s+reception\s+for\s+private\s+transfers?\b", "Private transfer may be requested locally", text, flags=re.IGNORECASE)
    text = re.sub(r"\baddon\s+cost\s+to\s+be\s+paid\s+on\s+ground\b", "additional cost, payable locally", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpaid\s+on\s+ground\b|\bpay\s+on\s+spot\b", "payable locally", text, flags=re.IGNORECASE)
    text = re.sub(r"\baddon\s+cost\b|\badd[- ]?on\s+cost\b", "additional cost", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*Private transfer", ". Private transfer", text)
    return polish_client_text(_clean_space(text)).strip(" .")


def split_self_transfer_notes(value: str) -> list[str]:
    """Return one or two polished bullets for mixed self-transfer rows."""

    source = repair_messy_client_text(value)
    lower_source = source.lower()
    cleaned: list[str] = []

    def add_note(note: str) -> None:
        note = repair_messy_client_text(note).strip(" .")
        note = re.sub(r"\bthe Bus Station\b", "the bus station", note)
        note = re.sub(r"\bthe Railway Station\b", "the railway station", note)
        if note and note not in cleaned:
            cleaned.append(note)

    # Compact supplier shorthands are often duplicated across title/details.
    # Parse the intended local movement once and keep the wording generic so a
    # terminal does not become an ugly destination headline.
    if re.search(r"\b(?:hotel|accommodation|your\s+hotel)\s+to\s+(?:the\s+)?airport\b", lower_source) or re.search(r"\bfrom\s+your\s+hotel\s+to\s+(?:the\s+)?airport\b", lower_source):
        add_note("Self-arranged transfer from your hotel to the airport")
    if re.search(r"\b(?:the\s+)?airport\s+to\s+(?:hotel|accommodation|your\s+accommodation)\b", lower_source) or re.search(r"\bfrom\s+(?:the\s+)?airport\s+to\s+your\s+accommodation\b", lower_source):
        add_note("Self-arranged transfer from the airport to your accommodation")
    if re.search(r"\b(?:hotel|accommodation|your\s+hotel)\s+to\s+(?:bus\s*station|bustation)\b", lower_source) or re.search(r"\bfrom\s+your\s+hotel\s+to\s+(?:the\s+)?bus\s+station\b", lower_source):
        add_note("Self transfer from your hotel to the bus station")
    if re.search(r"\b(?:bus\s*station|bustation)\s+to\s+(?:hotel|accommodation)\b", lower_source) or re.search(r"\bfrom\s+(?:the\s+)?bus\s+station\s+to\s+your\s+accommodation\b", lower_source):
        add_note("Self transfer from the bus station to your accommodation")
    if re.search(r"\b(?:hotel|accommodation|your\s+hotel)\s+to\s+(?:railway\s+station|train\s+station)\b", lower_source) or ("bus station" not in lower_source and re.search(r"\b(?:hotel|accommodation|your\s+hotel)\s+to\s+station\b", lower_source)):
        add_note("Self transfer from your hotel to the railway station")
    if re.search(r"\b(?:railway\s+station|train\s+station)\s+to\s+(?:hotel|accommodation)\b", lower_source) or ("bus station" not in lower_source and re.search(r"\bstation\s+to\s+(?:hotel|accommodation)\b", lower_source)):
        add_note("Self transfer from the railway station to your accommodation")

    if cleaned:
        if "private transfer may" in lower_source or "additional cost" in lower_source:
            add_note("Private transfer may be requested locally at additional cost")
        return cleaned

    text = clean_self_transfer_text(value)
    if not text:
        return []
    pieces = [piece.strip(" .") for piece in re.split(r"\.\s+", text) if piece.strip(" .")]
    for piece in pieces:
        piece = repair_messy_client_text(piece).strip(" .")
        if not piece:
            continue
        if piece.lower().startswith("self-arranged transfer"):
            # Normalize property typo/casing in common Levi rows.
            piece = re.sub(r"\bLevin\s+iglut\b", "Levin Iglut", piece, flags=re.IGNORECASE)
            piece = re.sub(r"\bLevi\s+Nordic\s+Star\b(?!\s+Igloos)", "Levi Nordic Star Igloos", piece, flags=re.IGNORECASE)
        if piece.lower().startswith("private transfer may"):
            piece = "Private transfer may be requested locally at additional cost"
        add_note(piece)
    return cleaned or [text]


def standardize_private_transfer_phrase(value: str, city: str = "") -> str:
    """Rewrite compact private transfer titles to full client wording."""

    text = repair_messy_client_text(value).strip(" .,-|:")
    city = canonicalize_place_name(city) or polish_title(city)
    lower = text.lower()

    def airport_name(default_city: str) -> str:
        # Preserve explicit airport names from source, e.g. Kittilä Airport.
        directional = re.search(rf"\b(?:to|from)\s+(?P<airport>{_PLACE_WORD_RE}?\s+Airport)\b", text, flags=re.IGNORECASE)
        if directional:
            airport = normalize_transport_place(directional.group("airport"))
            if airport.lower() in {"airport", "the airport"}:
                return "the airport"
            return airport
        airport_matches = re.findall(r"\b([A-ZÅÄÖÆØ][A-Za-zÀ-ÿøØåÅäÄöÖ .'-]{1,40}?\s+Airport)\b", text)
        if airport_matches:
            airport = normalize_transport_place(airport_matches[-1])
            if airport.lower() in {"airport", "the airport"}:
                return "the airport"
            return airport
        return f"{default_city} Airport" if default_city else "the airport"

    named_hotel_to_airport = re.search(r"\bprivate\s+(?:transfer\s+)?hotel\s+to\s+(?P<airport>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport)\b", text, flags=re.IGNORECASE)
    if named_hotel_to_airport:
        return f"Private transfer from your hotel to {normalize_transport_place(named_hotel_to_airport.group('airport'))}"
    named_airport_to_hotel = re.search(r"\bprivate\s+(?:transfer\s+)?(?P<airport>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport)\s+to\s+hotel\b", text, flags=re.IGNORECASE)
    if named_airport_to_hotel:
        return f"Private transfer from {normalize_transport_place(named_airport_to_hotel.group('airport'))} to your accommodation"

    if re.search(r"\bprivate\s+(?:transfer\s+)?airport\s+to\s+hotel\b", lower):
        return f"Private transfer from {airport_name(city)} to your accommodation"
    if re.search(r"\bprivate\s+(?:transfer\s+)?hotel\s+to\s+(?:the\s+)?airport\b", lower):
        return f"Private transfer from your hotel to {airport_name(city)}"
    if re.search(r"\bprivate\s+(?:transfer\s+)?station\s+to\s+hotel\b", lower):
        station = f"{city} Railway Station" if city else "the railway station"
        return f"Private transfer from {station} to your accommodation"
    if re.search(r"\bprivate\s+(?:transfer\s+)?(?:railway\s+)?station\s+to\s+(?:the\s+)?airport\b", lower):
        station = f"{city} Railway Station" if city else "the railway station"
        airport = f"{city} Airport" if city else "the airport"
        return f"Private transfer from {station} to {airport}"
    if re.search(r"\bprivate\s+(?:transfer\s+)?hotel\s+to\s+station\b", lower):
        station = f"{city} Railway Station" if city else "the railway station"
        return f"Private transfer from your hotel to {station}"
    if re.search(r"\bprivate\s+(?:transfer\s+)?port\s+to\s+hotel\b", lower):
        return "Private transfer from the port to your accommodation"
    if re.search(r"\bprivate\s+(?:transfer\s+)?hotel\s+to\s+port\b", lower):
        return "Private transfer from your hotel to the port"
    if re.search(r"\bprivate\s+(?:transfer\s+)?(?:bus\s*station|bustation)\s+to\s+hotel\b", lower):
        station = f"{city} Bus Station" if city else "the bus station"
        return f"Private transfer from {station} to your accommodation"
    if re.search(r"\bprivate\s+(?:transfer\s+)?hotel\s+to\s+(?:bus\s*station|bustation)\b", lower):
        station = f"{city} Bus Station" if city else "the bus station"
        return f"Private transfer from your hotel to {station}"
    # Explicit destination airport should still be cleaned even if source is
    # already partly expanded, e.g. "Private Hotel to Kittilä Airport".
    hotel_to_airport = re.search(r"\bprivate\s+(?:transfer\s+)?hotel\s+to\s+(?P<airport>[A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?\s+Airport)\b", text, flags=re.IGNORECASE)
    if hotel_to_airport:
        return f"Private transfer from your hotel to {normalize_transport_place(hotel_to_airport.group('airport'))}"
    return polish_title(text)


def scan_client_output(value: str) -> list[ClientOutputFinding]:
    text = str(value or "")
    findings: list[ClientOutputFinding] = []
    for code, pattern in RAW_CLIENT_OUTPUT_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        start = max(0, match.start() - 60)
        end = min(len(text), match.end() + 90)
        findings.append(ClientOutputFinding(code, pattern, text[start:end]))
    return findings


def has_client_output_leak(value: str) -> bool:
    return bool(scan_client_output(value))
