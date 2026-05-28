"""
text_polish.py

Client-facing text cleanup helpers for itinerary output.
These helpers silently fix recurring supplier/input text issues before the
content reaches the preview or PDF. They are intentionally conservative:
only common itinerary artifacts are corrected, and the raw input remains
unchanged.
"""

from __future__ import annotations

import re


def clean_space(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


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


def _apply_case_replacements(text: str) -> str:
    for pattern, replacement in CASE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def dedupe_or_similar(text: str) -> str:
    text = re.sub(r"\bor\s+Similar\b", "or similar", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:\s+or\s+similar){2,}", " or similar", text, flags=re.IGNORECASE)
    text = re.sub(r"\bor\s+similar\s+or\s+similar\b", "or similar", text, flags=re.IGNORECASE)
    return clean_space(text)


def remove_duplicate_service_phrase(text: str) -> str:
    """Remove repeated transfer/transport fragments from messy supplier cells."""
    text = clean_space(text)
    if not text:
        return ""

    # Specific but common artifact:
    # "Shuttle transfer from A to B Shuttle Transfer A to B"
    pattern = re.compile(
        r"\b(Shuttle transfer from\s+(.+?)\s+to\s+(.+?))\s+Shuttle\s+Transfer\s+\2\s+to\s+\3\b",
        flags=re.IGNORECASE,
    )
    text = pattern.sub(lambda m: m.group(1), text)

    # Generic adjacent duplicate phrase cleanup for short repeated tails.
    words = text.split()
    for n in range(3, min(10, len(words) // 2) + 1):
        first_tail = " ".join(words[-2 * n:-n]).lower()
        second_tail = " ".join(words[-n:]).lower()
        if first_tail == second_tail:
            return " ".join(words[:-n])

    return clean_space(text)


def _polish_text_fragment(text: str) -> str:
    """Polish one text fragment without intentionally preserving line breaks."""
    text = _apply_case_replacements(text)
    text = dedupe_or_similar(text)
    text = remove_duplicate_service_phrase(text)

    # Clean broken supplier inclusion fragments and recurring typo/casing issues.
    text = re.sub(r"\bRound-trip ferry is\b", "Round-trip ferry", text, flags=re.IGNORECASE)
    text = re.sub(r"\bKnowledgeable\s*,?\s*multilingual guide\b", "Knowledgeable, multilingual guide", text, flags=re.IGNORECASE)
    text = re.sub(r"\bEnglish\s+speaking\b", "English-speaking", text, flags=re.IGNORECASE)
    text = re.sub(r"\bA/C\b", "air-conditioned", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPick/Drop\b", "Pick-up/drop-off", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPick\s*up\b", "Pick-up", text, flags=re.IGNORECASE)
    text = re.sub(r"\bDrop\s*off\b", "drop-off", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpick-up/drop-off\b", "Pick-up/drop-off", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTour Guiding\b", "Local guide service", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTour guiding\b", "Local guide service", text, flags=re.IGNORECASE)
    text = re.sub(r"\bProfessional Camera Pictures\b", "Professional camera photos", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTour Transportation\b", "Transport during the tour", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTour transportation\b", "Transport during the tour", text, flags=re.IGNORECASE)
    text = re.sub(r"\bGoods\s*&\s*services tax\b", "Taxes and service fees", text, flags=re.IGNORECASE)
    text = re.sub(r"\bDSLR photography\b", "DSLR photography", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+)\s*KM\b", lambda m: f"{m.group(1)} km", text, flags=re.IGNORECASE)
    text = re.sub(r"\bRovaniemi City\b", "Rovaniemi city", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCookies\s*&\s*hot drinks\b", "Cookies and hot drinks", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCookies\s*&\s*Hot drinks\b", "Cookies and hot drinks", text, flags=re.IGNORECASE)
    text = re.sub(r"\bHot\s+drinks?\s*&\s*snacks?\s+or\s+cookies\b", "Hot drinks and snacks or cookies", text, flags=re.IGNORECASE)
    text = re.sub(r"\bHot\s+drinks?\s+and\s+snacks?\s+or\s+cookies\b", "Hot drinks and snacks or cookies", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcolder lagoon\b", "cold lagoon", text, flags=re.IGNORECASE)
    text = re.sub(r"\bin central of\s+", "in central ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPick-up/drop-off in central of\s+", "Pick-up/drop-off in central ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bFull\s+Pention\b", "Full pension", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfull day transportation\b", "Full-day transportation", text, flags=re.IGNORECASE)
    text = re.sub(r"\bguide and entrance tickets to all the sites\b", "Guide and entrance tickets to all sites", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfrederiksborg palace\b", "Frederiksborg Palace", text, flags=re.IGNORECASE)
    text = re.sub(r"\broskilde cathedral\b", "Roskilde Cathedral", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthe viking ship museum\b", "the Viking Ship Museum", text, flags=re.IGNORECASE)
    text = re.sub(r"\bFLybus\b", "Flybus", text, flags=re.IGNORECASE)
    text = re.sub(r"\bFlyBus\b", "Flybus", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCity Centre\b", "city centre", text, flags=re.IGNORECASE)
    text = re.sub(r"\bReykajvik\b|\bReykavik\b", "Reykjavík", text, flags=re.IGNORECASE)

    # Normalize compact supplier time text such as "between 8am and 8.30"
    # before punctuation spacing runs. This keeps group-tour descriptions
    # readable without changing non-time decimal values elsewhere.
    text = re.sub(r"(?<!:)(?<!\d)(\d{1,2})\s*a\.?m\.?\b", r"\1:00 AM", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!:)(?<!\d)(\d{1,2})\s*p\.?m\.?\b", r"\1:00 PM", text, flags=re.IGNORECASE)
    text = re.sub(r"(\bbetween\s+\d{1,2}:\d{2}\s+(?:AM|PM)\s+and\s+)(\d{1,2})\.(\d{2})", r"\1\2:\3", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbetween\s+(\d{1,2}:\d{2})\s+AM\s+and\s+(\d{1,2}:\d{2})(?!\s*(?:AM|PM|noon))", r"between \1 AM and \2 AM", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbetween\s+(\d{1,2}:\d{2})\s+PM\s+and\s+(\d{1,2}:\d{2})(?!\s*(?:AM|PM|noon))", r"between \1 PM and \2 PM", text, flags=re.IGNORECASE)

    # Normalize punctuation spacing, but never insert spaces inside clock times
    # such as 10:30 AM or 3:00 PM.
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"([,.;])(?=\S)", r"\1 ", text)
    text = re.sub(r"(?<!\d):(?!\d)(?=\S)", ": ", text)
    text = re.sub(r"\b(\d{1,2}):\s+(\d{2})\s*([AP]M)\b", r"\1:\2 \3", text, flags=re.IGNORECASE)
    return clean_space(text)


def polish_client_text(value: str) -> str:
    """General client-facing text polish.

    Multiline supplier blocks must keep their line breaks because the parser uses
    those line breaks to create separate inclusion bullets. Earlier versions
    collapsed multiline text too early, which made several inclusions spill into
    one long bullet and into pick-up/drop-off fields.
    """
    if value is None:
        return ""

    text = str(value).replace("\xa0", " ")

    if "\n" in text:
        return "\n".join(_polish_text_fragment(line) for line in text.splitlines())

    return _polish_text_fragment(text)

def polish_hotel_name(value: str) -> str:
    text = polish_client_text(value)
    text = re.sub(r"\s+or\s+similar$", "", text, flags=re.IGNORECASE).strip()

    # Remove street-address suffixes that suppliers sometimes append to hotel
    # names, for example "Santa's Hotel Santa Claus Korkalonkatu 29".
    address_suffix = (
        r"\s+[A-ZÀ-ÝÆØÅÄÖ][A-Za-zÀ-ÿÆØÅÄÖæøåäö'’.-]*"
        r"(?:katu|gata|gatan|veien|vegen|vej|road|street|avenue|ave|lane|ln|boulevard|blvd)"
        r"\s+\d+[A-Za-z]?\s*$"
    )
    text = re.sub(address_suffix, "", text, flags=re.IGNORECASE).strip()

    text = dedupe_or_similar(text)
    return text




_TITLE_SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into",
    "nor", "of", "on", "onto", "or", "per", "the", "to", "via", "with",
}

_TITLE_REPLACEMENTS = [
    (r"\bnorway\s+in\s+a\s+nutshell\b", "Norway in a Nutshell"),
    (r"\bsanta\s+claus\b", "Santa Claus"),
    (r"\bnorthern\s+lights\b", "Northern Lights"),
    (r"\bblue\s+lagoon\b", "Blue Lagoon"),
    (r"\bsky\s+lagoon\b", "Sky Lagoon"),
    (r"\bflåm\b|\bflam\b", "Flåm"),
    (r"\bflåmsbana\b|\bflamsbana\b", "Flåmsbana"),
    (r"\bfløibanen\b|\bfloibanen\b", "Fløibanen"),
    (r"\bnærøyfjord\b|\bnaeroyfjord\b", "Nærøyfjord"),
    (r"\bthingvellir\b", "Thingvellir"),
    (r"\bþingvellir\b", "Þingvellir"),
    (r"\bgeysir\b", "Geysir"),
    (r"\bgullfoss\b", "Gullfoss"),
    (r"\breykjav[ií]k\b", "Reykjavík"),
    (r"\btroms[oø]\b", "Tromsø"),
    (r"\brovaniemi\b", "Rovaniemi"),
    (r"\bhelsinki\b", "Helsinki"),
    (r"\btallinn\b", "Tallinn"),
    (r"\bcopenhagen\b", "Copenhagen"),
    (r"\bsvolv[aæ]r\b|\bsvolvaer\b|\bsvolaver\b", "Svolvær"),
    (r"\bgothenburg\b|\bgothernburg\b", "Gothenburg"),
    (r"\bstockholm\b", "Stockholm"),
    (r"\bmalm[oø]\b", "Malmö"),
    (r"\bkirkenes\b", "Kirkenes"),
    (r"\bbergen\b", "Bergen"),
    (r"\boslo\b", "Oslo"),
    (r"\bvatnaj[oö]kull\b", "Vatnajökull"),
    (r"\bj[oö]kuls[aá]rl[oó]n\b", "Jökulsárlón"),
    (r"\bsnæfellsnes\b|\bsnaefellsnes\b", "Snæfellsnes"),
    (r"\bborgarfj[oö]r[dð]ur\b", "Borgarfjörður"),
    (r"\bkval[oø]ya\b", "Kvaløya"),
    (r"\bsommar[oø]y\b", "Sommarøy"),
    (r"\bsuomenlinna\b", "Suomenlinna"),
]

_ACRONYM_REPLACEMENTS = [
    (r"\batv\b", "ATV"),
    (r"\bsuv\b", "SUV"),
    (r"\bbus\b", "bus"),
    (r"\bwifi\b", "WiFi"),
    (r"\bwi-fi\b", "Wi-Fi"),
    (r"\bq&a\b", "Q&A"),
    (r"\bbq\b", "BBQ"),
]

_PRICE_FRAGMENT_PATTERNS = [
    r"\b(?:optional\s+add[- ]?on\s*)?at\s*(?:from\s*)?(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)\s*\d[\d.,]*(?:\s*/\s*(?:person|pax|passenger|adult|child))?",
    r"\b(?:optional\s+add[- ]?on\s*)?at\s*(?:from\s*)?\d[\d.,]*\s*(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)(?:\s*/\s*(?:person|pax|passenger|adult|child))?",
    r"\b(?:price|cost|supplement|single traveler supplement fee)\s*(?:is|from|at|:)?\s*(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)?\s*\d[\d.,]*(?:\s*(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£))?(?:\s*(?:per|/ )\s*(?:person|pax|passenger|adult|child))?",
    r"\b\d[\d.,]*\s*(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)\s*(?:per|/)?\s*(?:person|pax|passenger|adult|child)?",
    r"\b(?:NOK|EUR|USD|GBP|DKK|SEK|ISK|kr|€|\$|£)\s*\d[\d.,]*\s*(?:per|/)?\s*(?:person|pax|passenger|adult|child)?",
    r"\bprice\s+is\s+per\s+(?:passenger|person|pax)\b",
]


def strip_price_fragments(value: str) -> str:
    """Remove prices from optional add-ons without removing the experience itself."""
    text = str(value or "")
    if not text:
        return ""
    for pattern in _PRICE_FRAGMENT_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bOptional\s+Add[- ]?on\b\s*[:|,-]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bOptinal\s+Add[- ]?on\b\s*[:|,-]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\|\s*\|\s*", " | ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return clean_space(text).strip(" -:|,.;")


def _looks_over_capitalized_title(text: str) -> bool:
    words = re.findall(r"[A-Za-zÀ-ÿÆØÅÄÖæøåäö']+", text)
    if len(words) < 3:
        return False
    titled = sum(1 for word in words if word[:1].isupper() and word[1:].islower())
    small_caps = sum(1 for word in words if word.lower() in _TITLE_SMALL_WORDS and word[:1].isupper())
    letters = [ch for ch in text if ch.isalpha()]
    upper_ratio = sum(1 for ch in letters if ch.isupper()) / max(len(letters), 1)
    return upper_ratio > 0.55 or (titled >= max(3, len(words) - 1) and small_caps > 0)


def sentence_style_title(value: str) -> str:
    """Return a grammatical client-facing title, not blind title case."""
    text = polish_client_text(value).strip(" -:|")
    if not text:
        return ""

    # Supplier cells often contain all-caps or title-case marketing titles.
    if _looks_over_capitalized_title(text):
        words = re.split(r"(\s+|-)", text)
        out = []
        word_index = 0
        for token in words:
            if not token or token.isspace() or token == "-":
                out.append(token)
                continue
            leading = re.match(r"^([^A-Za-zÀ-ÿÆØÅÄÖæøåäö']*)", token).group(1)
            trailing = re.search(r"([^A-Za-zÀ-ÿÆØÅÄÖæøåäö']*)$", token).group(1)
            core = token[len(leading): len(token) - len(trailing) if trailing else len(token)]
            lower_core = core.lower()
            if word_index == 0:
                new_core = lower_core[:1].upper() + lower_core[1:]
            elif lower_core in _TITLE_SMALL_WORDS:
                new_core = lower_core
            elif core.isupper() or (core[:1].isupper() and core[1:].islower()):
                new_core = lower_core
            else:
                new_core = core
            out.append(f"{leading}{new_core}{trailing}")
            word_index += 1
        text = "".join(out)

    for pattern, replacement in _TITLE_REPLACEMENTS + _ACRONYM_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Common grammatical fix shown by the itinerary owner as a quality gate.
    text = re.sub(r"\bMeet Santa Claus and His Friends\b", "Meet Santa Claus and his friends", text, flags=re.IGNORECASE)
    text = re.sub(r"\bSanta Claus and His Friends\b", "Santa Claus and his friends", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwith\s+transfers\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bWatch\s+Whales\b", "Whale Watching", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    return clean_space(text).strip(" -:|")


def polish_title(value: str) -> str:
    text = sentence_style_title(value)
    text = dedupe_or_similar(text)
    return text.strip(" -:|")


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

# Shared time/duration helpers are re-exported here for backward compatibility.
# The implementation lives in time_utils.py so parser, normalizer, preview and
# PDF export all use the same formatting rules.
from time_utils import (
    parse_duration_minutes,
    expand_time_with_duration,
    format_duration_display,
    format_duration_minutes,
)
