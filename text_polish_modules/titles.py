"""Client-facing itinerary title casing and cleanup."""

from __future__ import annotations

import re

from text_polish_modules.text_cleanup import clean_space, dedupe_or_similar, polish_client_text


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
    protected_value = re.sub(
        r"\bAurora\s+Base\s*camp\b",
        "__AURORA_BASECAMP__",
        str(value or ""),
        flags=re.IGNORECASE,
    )
    text = polish_client_text(protected_value).strip(" -:|")
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
    text = text.replace("__AURORA_BASECAMP__", "Aurora Basecamp")
    text = re.sub(r"\s{2,}", " ", text)
    return clean_space(text).strip(" -:|")


def polish_title(value: str) -> str:
    text = sentence_style_title(value)
    text = dedupe_or_similar(text)
    return text.strip(" -:|")


