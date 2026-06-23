"""Client-facing text cleanup helpers for itinerary output."""

from __future__ import annotations

import re
from functools import lru_cache


def clean_space(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()



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


def _apply_case_replacements(text: str) -> str:
    for pattern, replacement in COMPILED_CASE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
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


@lru_cache(maxsize=8192)
def _polish_text_fragment(text: str) -> str:
    """Polish one text fragment without intentionally preserving line breaks."""
    text = _apply_case_replacements(text)
    text = dedupe_or_similar(text)
    text = remove_duplicate_service_phrase(text)

    # Remove low-value supplier metadata that should never be visible to clients.
    # Commercial conditions must not disappear during prose cleanup.  Supplier
    # shorthand such as ``(if snow)`` changes whether a service is guaranteed;
    # rewrite it into client-facing wording instead of deleting it.  Pure sales
    # qualifiers such as ``(unlimited)`` can still be removed safely.
    text = re.sub(r"\s*\(\s*if\s+snow\s*\)", " if snow conditions allow", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\s*\(\s*(?:weather\s+permitting|if\s+weather\s+permits)\s*\)",
        " if weather permits",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*\(\s*unlimited\s*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bto\s+Airport\b", "to the airport", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAurora\s+Borealis\b", "Northern Lights", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAuroras\b", "Northern Lights", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAurora\b", "Northern Lights", text, flags=re.IGNORECASE)

    # Clean awkward supplier punctuation/quote residue that otherwise reaches
    # meeting points and descriptions in preview/PDF.
    text = re.sub(
        r"\bby\s+[‘’'\"]{1,2}\s*([^‘’'\"]+?)\s*[‘’'\"]{1,2}\s+sign\b",
        lambda m: f"by the “{clean_space(m.group(1))}” sign",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\baboard\s*&\s*(?=[A-Za-zÀ-ÿ])", "aboard a ", text, flags=re.IGNORECASE)
    text = re.sub(r"\belectric\s*,\s*boat\b", "electric boat", text, flags=re.IGNORECASE)

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
    text = re.sub(r"\bReyakjvik\b|\bReykajvik\b|\bReykavik\b|\bReykjavik\b", "Reykjavík", text, flags=re.IGNORECASE)
    text = re.sub(r"\bHlesinkih?\b|\bHellsinki\b|\bHelisnki\b", "Helsinki", text, flags=re.IGNORECASE)
    text = re.sub(r"\bNUtsheel\b|\bNutsheel\b|\bNuthsell\b|\bNUtshell\b", "Nutshell", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTallinnn\b|\bTallin\b", "Tallinn", text, flags=re.IGNORECASE)
    text = re.sub(r"\bTromso\b", "Tromsø", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAlesund\b", "Ålesund", text, flags=re.IGNORECASE)
    text = re.sub(r"\bFlam\b|\bFLam\b", "Flåm", text, flags=re.IGNORECASE)
    text = re.sub(r"\bKakslauttenen\b", "Kakslauttanen", text, flags=re.IGNORECASE)
    text = re.sub(r"\bSaariselka\b", "Saariselkä", text, flags=re.IGNORECASE)
    text = re.sub(r"\bProfesional\b", "Professional", text, flags=re.IGNORECASE)
    text = re.sub(r"\bEngish\b", "English", text, flags=re.IGNORECASE)
    text = re.sub(r"\bticktes\b", "tickets", text, flags=re.IGNORECASE)
    text = re.sub(r"\btickert\b", "ticket", text, flags=re.IGNORECASE)
    text = re.sub(r"\bavaiable\b", "available", text, flags=re.IGNORECASE)
    text = re.sub(r"\barrnaged\b", "arranged", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAfternon\b", "Afternoon", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMelas\s+onboard\b", "Meals onboard", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCLaus\b", "Claus", text, flags=re.IGNORECASE)
    text = re.sub(r"\bVIllage\b", "Village", text, flags=re.IGNORECASE)
    text = re.sub(r"\badditonal\b", "additional", text, flags=re.IGNORECASE)

    # Keep client-facing wording grounded. Supplier labels sometimes use
    # expensive-sounding adjectives for standard room categories, coaches or
    # tickets; the itinerary should describe the concrete item instead.
    original_leading_sales_adjective = re.match(
        r"^\s*(?:premium|luxurious|luxury|hi[- ]?end|high[- ]end|upscale|bespoke|vip)\s+\w",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bPremium\s+coach\b", "Coach", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+bus\b", "Bus", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+vehicle\b", "Vehicle", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+transfer\b", "Transfer", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+Double\s+Igloo\b", "__PREMIUM_DOUBLE_IGLOO__", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+Glass\s+Igloo\b", "__PREMIUM_GLASS_IGLOO__", text, flags=re.IGNORECASE)
    # Preserve supplier room categories such as "Premium Double Igloo" and
    # "Premium Glass Igloo". Premium can be part of the sold room type here.
    text = re.sub(r"\bPremium\s+(?=(?:waterfront|sea|fjord|mountain|view|standard|double|twin|single|suite|room)\b)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPremium\s+(?=(?:entry|admission|ticket|tickets)\b)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:hi[- ]?end|high[- ]end|upscale|luxurious|luxury|bespoke|vip)\s+coach\b", "Coach", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:hi[- ]?end|high[- ]end|upscale|luxurious|luxury|bespoke|vip)\s+bus\b", "Bus", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:hi[- ]?end|high[- ]end|upscale|luxurious|luxury|bespoke|vip)\s+(?=(?:vehicle|transfer|room|stay|experience|tour|ticket|tickets|entry|admission)\b)", "", text, flags=re.IGNORECASE)
    # Remove standalone sales adjectives from visible client-facing supplier
    # fragments as well. For example, food-tour inclusions like
    # "Luxurious cardamom twist" should become the factual item
    # "Cardamom twist" rather than repeating expensive-sounding marketing
    # language.
    leading_sales_adjective = re.match(
        r"^\s*(?:premium|luxurious|luxury|hi[- ]?end|high[- ]end|upscale|bespoke|vip)\s+\w",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:premium|luxurious|luxury|hi[- ]?end|high[- ]end|upscale|bespoke|vip)\s+(?=\w)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\belectric\s*,\s*boat\b", "electric boat", text, flags=re.IGNORECASE)
    text = re.sub(r"\baboard\s*&\s*(?=[A-Za-zÀ-ÿ])", "aboard a ", text, flags=re.IGNORECASE)
    text = text.replace("__PREMIUM_DOUBLE_IGLOO__", "Premium Double Igloo").replace("__PREMIUM_GLASS_IGLOO__", "Premium Glass Igloo")
    if original_leading_sales_adjective or leading_sales_adjective:
        text = re.sub(r"^(\s*)([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), text, count=1)

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
    # Hotel names are source-owned product strings.  General client prose may
    # rewrite "Aurora" to "Northern Lights", but that must never rename a
    # property such as "Home Hotel Aurora" or "Clarion Collection Aurora".
    raw_text = str(value or "")
    protected = re.sub(r"\bAurora\b", "__HOTEL_AURORA__", raw_text, flags=re.IGNORECASE)
    text = polish_client_text(protected)
    text = text.replace("__HOTEL_AURORA__", "Aurora")
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




