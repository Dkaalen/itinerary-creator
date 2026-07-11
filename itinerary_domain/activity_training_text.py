"""Text normalization and field parsing for activity-training data."""

from functools import lru_cache
import re
import unicodedata
from text_polish import polish_client_text, polish_title

STOPWORDS = {"a","an","and","at","by","day","for","from","in","incl","including","of","on","or","the","to","tour","trip","with","without","experience","activity","ticket","tickets","entry","admission","only","included","includes"}
SYNONYMS = {"aurora":"northern lights","basecamp":"base camp","sami":"sámi","saami":"sámi","floibanen":"fløibanen","flam":"flåm","tromso":"tromsø","reykjavik":"reykjavík","alesund":"ålesund","svolvaer":"svolvær","saariselka":"saariselkä","kakslauttenen":"kakslauttanen","tallin":"tallinn","nutsheel":"nutshell","nutshelll":"nutshell"}
SYNONYM_PATTERNS = tuple((re.compile(rf"\b{re.escape(source)}\b", re.I), replacement) for source,replacement in SYNONYMS.items())
TIME_RE = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", re.I); DURATION_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:hrs?|hours?|minutes?|mins?)\b", re.I); NON_WORD_RE = re.compile(r"[^a-z0-9åäöøæéáíóúýþðàèìòùñçšžœßà-ÿ]+"); SPACE_RE = re.compile(r"\s+")


def ascii_key(value: str) -> str: return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()


@lru_cache(maxsize=16384)
def normalize_training_text(value: str) -> str:
    text = str(value or "").replace("\xa0", " ").lower()
    for pattern,replacement in SYNONYM_PATTERNS: text = pattern.sub(replacement,text)
    return SPACE_RE.sub(" ", NON_WORD_RE.sub(" ", DURATION_RE.sub(" ", TIME_RE.sub(" ", text)))).strip()


@lru_cache(maxsize=16384)
def training_tokens(value: str) -> frozenset[str]:
    tokens = {item for item in normalize_training_text(value).split() if len(item)>2 and item not in STOPWORDS}
    if {"northern","lights"} <= tokens: tokens.add("northern_lights")
    if {"base","camp"} <= tokens: tokens.add("base_camp")
    return frozenset(tokens)


def field_from_details(details: str,label: str) -> str:
    match = re.compile(rf"\s+-\s+{re.escape(label)}\s*:\s*(.*?)(?=\s+-\s+(?:Time|Meeting point|Inclusions|Description)\s*:|$)",re.I|re.S).search(details)
    return polish_client_text(match.group(1).strip()) if match else ""


def title_from_details(city: str, details: str) -> str:
    text = str(details or "").strip()
    if city and text.lower().startswith(f"{city.lower()}:"): text=text.split(":",1)[1].strip()
    text=re.split(r"\s+-\s+Time\s*:",text,maxsplit=1,flags=re.I)[0].strip(" -:|"); title=polish_title(text)
    if re.search(r"aurora\s+basecamp|aurora\s+base\s+camp",text,re.I): title=re.sub(r"Northern Lights Base\s*camp","Aurora Basecamp",title,flags=re.I)
    return title


def split_inclusions(value: str) -> tuple[str,...]:
    if not value or value.lower()=="not specified": return ()
    parts=re.split(r"\s*;\s*|\s*,\s*(?=(?:professional|english|knowledgeable|round|hotel|transport|pick|drop|warm|snacks|drinks|ticket|guided|visit|cruise|free|lunch|meal|thermal|winter|hot|snow|reindeer|husky|santa|short|storytelling|traditional)\b)",value,flags=re.I);clean=[]
    for part in parts:
        item=polish_client_text(part).strip(" .;,-")
        if item and item not in clean and item.lower()!="not specified": clean.append(item)
    return tuple(clean)
