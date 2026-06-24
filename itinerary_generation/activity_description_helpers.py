"""Activity description helpers used by legacy UI rendering."""

from __future__ import annotations

import re

from itinerary_generation.titles import create_client_activity_title
from text_polish import polish_client_text, polish_title
from itinerary_generation.render_text_helpers import get_detail_level_name
from itinerary_generation.activity_training_catalogue import catalogue_description_for_row
from itinerary_generation.product_rules import find_product_match


_SUPPLIER_SECTION_LABEL_RE = re.compile(
    r"^\s*(?:overview|what(?:'|’)s included\??|what to expect\??|please note:?|not included:?|includes?:?|pick up\s*/\s*meeting point|meeting point)\s*$",
    flags=re.IGNORECASE,
)

_BAD_DESCRIPTION_FALLBACK_MARKERS = [
    "join a whale watching experience",
    "join a guided glacier experience",
    "enjoy a planned experience",
    "enjoy a guided experience",
    "enjoy this lagoon and wellness experience",
]



__all__ = [
    "_BAD_DESCRIPTION_FALLBACK_MARKERS",
    "_SUPPLIER_SECTION_LABEL_RE",
    "_extract_section_after_label",
    "_real_supplier_description",
    "_strip_supplier_day_heading",
    "_trim_description_sentences",
    "get_activity_description",
]
def _strip_supplier_day_heading(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    lines = text.split("\n")
    if lines:
        lines[0] = re.sub(r"^\s*Day\s*\d+\s*[:\-–]\s*[^\n|]+\s*", "", lines[0], flags=re.IGNORECASE).strip()
    return "\n".join(line for line in lines if line.strip()).strip()


def _extract_section_after_label(text: str, labels: tuple[str, ...]) -> str:
    lines = [line.strip() for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    capture = False
    out: list[str] = []
    label_patterns = tuple(label.lower() for label in labels)
    for line in lines:
        clean = line.strip(" :-")
        lower = clean.lower()
        if not capture and any(lower.startswith(label) for label in label_patterns):
            capture = True
            remainder = re.sub(r"^\s*(?:" + "|".join(re.escape(label) for label in labels) + r")\s*[:?\-]*\s*", "", line, flags=re.IGNORECASE).strip()
            if remainder:
                out.append(remainder)
            continue
        if capture:
            if _SUPPLIER_SECTION_LABEL_RE.match(clean):
                break
            out.append(line)
    return "\n".join(out).strip()


def _trim_description_sentences(text: str, max_words: int = 90, min_sentences: int = 2) -> str:
    cleaned = polish_client_text(_strip_supplier_day_heading(text))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|•")
    if not cleaned:
        return ""
    # Remove supplier sales closers that read poorly in a client proposal.
    cleaned = re.sub(r"\b(?:What are you waiting for\?|Start your adventure now by booking a date\.?|Come and join us[^.?!]*[.?!])", "", cleaned, flags=re.IGNORECASE).strip()
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    selected: list[str] = []
    word_count = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        words = sentence.split()
        if selected and word_count + len(words) > max_words and len(selected) >= min_sentences:
            break
        selected.append(sentence)
        word_count += len(words)
        if word_count >= max_words and len(selected) >= min_sentences:
            break
    result = " ".join(selected).strip()
    if len(result.split()) < 12:
        return ""
    return result


def _real_supplier_description(row: dict, max_words: int = 90) -> str:
    """Prefer real supplier prose over generic fallbacks.

    This is intentionally broad and data-driven: if the row has a substantial
    day/activity body, use it before any keyword fallback such as whale/glacier.
    """
    raw_sources = [row.get("description", ""), row.get("details", ""), row.get("original_title", "")]
    for raw in raw_sources:
        text = str(raw or "")
        if not text.strip():
            continue
        # Prefer explicit narrative sections in supplier rows.
        for labels in (("What to expect", "What to expect?"), ("Overview",), ("Description",)):
            section = _extract_section_after_label(text, labels)
            candidate = _trim_description_sentences(section, max_words=max_words)
            if candidate:
                return candidate
        # Rows that only contain title/time/meeting/includes metadata do not
        # have narrative prose. Let the planned fallback write the description.
        if not re.match(r"^\s*Day\s*\d+\s*[:\-–]", text, flags=re.IGNORECASE):
            lower_text = text.lower()
            has_metadata = any(marker in lower_text for marker in [" time:", " meeting point", " includes:", " what's included", " what’s included"])
            pipe_parts = [part.strip() for part in re.split(r"\s*\|\s*", text) if part.strip()]
            has_pipe_metadata = len(pipe_parts) >= 3 and any(
                re.search(r"\b(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d+(?:\.\d+)?\s*(?:hrs?|hours?))\b", part, flags=re.IGNORECASE)
                for part in pipe_parts[1:]
            )
            has_section = any(marker in lower_text for marker in ["overview", "what to expect", "description:"])
            if (has_metadata or has_pipe_metadata) and not has_section:
                continue
        candidate = _trim_description_sentences(text, max_words=max_words)
        if candidate:
            return candidate
    return ""


def get_activity_description(row, detail_level=None):
    detail_level = detail_level or get_detail_level_name()
    title = f'{row.get("title", "")} {row.get("original_title", "")} {row.get("details", "")}'.lower()
    city = str(row.get("city", "")).strip().lower()

    real_description = _real_supplier_description(row, max_words=115 if re.search(r"^\s*Day\s*\d+\s*:", str(row.get("details", "")), flags=re.IGNORECASE) else 85)
    if real_description:
        return real_description

    product_match = find_product_match(row)
    if product_match and product_match.description:
        return product_match.description

    if "icebreaker" in title and "cruise" in title:
        return "Experience the Arctic coastline from an icebreaker cruise, with time on the frozen sea and the included floating experience arranged as part of the excursion."

    if "wildlife photography" in title and "longyearbyen" in title:
        return "Spend time looking for Arctic wildlife and landscape photo opportunities around Longyearbyen with the guidance arranged for the experience."

    if "mountain hike" in title and "abisko" in title:
        return "Hike in the Abisko mountain landscape, with time for views, local nature stories and the included food stop during the excursion."

    if "fjord" in title and ("minivan" in title or "vip" in title or "kvaløya" in title or "sommarøy" in title):
        return "Explore the coastal scenery around Tromsø by road, with fjords, mountains, beaches and Arctic landscapes forming the focus of the day."

    if "lofoten" in title and "trollfjord" in title:
        if detail_level == "Elegant concise":
            return "Travel through Lofoten by land and sea, including Trollfjord scenery."
        if detail_level == "Rich descriptive":
            return "Experience Lofoten by land and sea, with a scenic cruise into the dramatic Trollfjord landscape."
        return "Travel through Lofoten by land and sea, with a scenic cruise into the dramatic Trollfjord."

    if "city walking" in title and "canal" in title and "copenhagen" in title:
        if detail_level == "Elegant concise":
            return "Explore Copenhagen on foot and by canal with a local host."
        if detail_level == "Rich descriptive":
            return "Explore central Copenhagen with a local host, combining city landmarks, local stories, and a scenic canal experience."
        return "Explore central Copenhagen on foot with a local host, including key landmarks and a scenic canal experience."

    if "essential oslo" in title:
        if detail_level == "Elegant concise":
            return "Explore central Oslo on foot with a local guide."
        if detail_level == "Rich descriptive":
            return "Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital."
        return "Explore central Oslo on foot with a local guide, including key landmarks around the city center."

    if "guided walking tour" in title:
        if "copenhagen" in city or "copenhagen" in title:
            if detail_level == "Elegant concise":
                return "Explore central Copenhagen on foot with a local guide."
            if detail_level == "Rich descriptive":
                return "Explore central Copenhagen on foot with a local guide, with time for local stories, major landmarks, and the atmosphere of the city."
            return "Explore central Copenhagen on foot with a local guide, with time for local stories and key city landmarks."
        if "oslo" in city or "oslo" in title:
            if detail_level == "Elegant concise":
                return "Explore central Oslo on foot with a local guide."
            if detail_level == "Rich descriptive":
                return "Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital."
            return "Explore central Oslo on foot with a local guide, including key landmarks around the city center."

    if "must-see bergen" in title or ("foot and boat" in title and "bergen" in title):
        if detail_level == "Elegant concise":
            return "Explore Bergen on foot and by boat."
        if detail_level == "Rich descriptive":
            return "Explore Bergen from two perspectives: on foot through the historic city streets and by boat from the surrounding waters."
        return "Explore Bergen on foot and by boat, combining historic city streets with a scenic perspective from the water."

    if "hop on" in title or "hop-on" in title or "hop off" in title or "hop-off" in title:
        if detail_level == "Rich descriptive":
            return "Use your flexible ticket to explore the city at your own pace, choosing the stops and sights that suit your day best."
        return "Use your flexible ticket to explore the city at your own pace."

    # The training catalogue is a structured example layer, not the highest
    # authority.  Use it after explicit supplier prose and specific product
    # templates, but before broad keyword fallbacks such as generic walking,
    # boat, Northern Lights, or planned-experience copy.
    catalogue_description = catalogue_description_for_row(row)
    if catalogue_description:
        return catalogue_description

    clean_title = polish_title(create_client_activity_title(row) or row.get("title", "") or "Included experience")
    city_name = polish_title(row.get("city", ""))
    destination_phrase = f" in {city_name}" if city_name else ""
    combined = f"{clean_title} {title}".lower()

    # Fallback descriptions should add atmosphere, not repeat logistics already
    # shown in the Time / Duration / Pick-up lines. They must never inject
    # destination-specific content that is not supported by the current row.
    if "blue lagoon" in combined or "sky lagoon" in combined or "lagoon" in combined and ("admission" in combined or "spa" in combined or "ritual" in combined):
        return "Enjoy this lagoon and wellness experience, with admission details arranged as part of the day."
    if "whale watching" in combined or "whale" in combined:
        return f"Join a whale watching experience{destination_phrase}, with time on the water and guidance from the local crew."
    if "snork" in combined or "silfra" in combined:
        return f"Experience Silfra with the arranged equipment and local guidance, following the meeting details provided for the activity."
    if "atv" in combined or "quad" in combined:
        return f"Head out on an ATV experience, with safety equipment and guidance provided for the route."
    if "glacier" in combined or "crampon" in combined:
        return f"Join a guided glacier experience, with the required safety equipment provided before heading onto the ice."
    if "suomenlinna" in combined:
        return "A guided introduction to Helsinki’s city highlights combined with a visit to the historic sea fortress island of Suomenlinna."
    if ("reindeer feeding" in combined or "sámi" in combined or "sami" in combined) and not ("northern lights chase" in combined or "northern lights hunt" in combined or "aurora hunt" in combined):
        return "Meet the reindeer herd, learn about Sámi culture and enjoy a warm meal as part of the Arctic experience."
    if "northern lights basecamp" in combined:
        return "Spend the evening at a dedicated Northern Lights basecamp, with time to wait for the aurora in a comfortable Arctic setting."
    if "northern lights" in combined or "aurora" in combined:
        if "reindeer" in combined and ("hunt" in combined or "chase" in combined):
            return "Head into the winter landscape for a Northern Lights hunt by reindeer, with warm drinks and Arctic atmosphere included in the experience."
        if "bbq" in combined or "barbecue" in combined or "lappish" in combined:
            return "Head away from the city lights in search of the Northern Lights, with a Lappish barbecue and time by the fire in the winter landscape."
        if "hunt" in combined or "chase" in combined:
            return "Head out in search of the Northern Lights with local guidance, using the evening conditions to find the best available viewing areas."
        if "floating" in combined or "float" in combined:
            return "Experience the Arctic night from a peaceful frozen-lake setting, with specialist equipment provided for the ice-floating experience."
        return "Enjoy an evening Northern Lights experience designed around the Arctic sky, local conditions, and the chance to see the aurora."
    if "ranua" in combined:
        return "Travel to Ranua Wildlife Park for a look at Arctic wildlife in a forested Lapland setting, with time to enjoy the experience at an easy pace."
    if "wildlife" in combined:
        return f"Enjoy a wildlife-focused experience{destination_phrase}, with the details arranged as part of the day."
    if "fjord tour" in combined or "kvaløya" in combined or "sommarøy" in combined:
        return "Explore the coastal scenery around Tromsø, with fjords, islands and Arctic landscapes forming the focus of the day."
    if "funicular" in combined or "fløibanen" in combined:
        return "Ride the Fløibanen funicular for an easy ascent above Bergen and views over the city, harbour and surrounding mountains."

    if "photo tour" in combined and ("fjord" in combined or "landscape" in combined):
        return f"Explore scenic fjords and Arctic landscapes{destination_phrase}, with guidance on viewpoints and photography along the way."
    if "walking" in combined or "guided" in combined:
        return f"Enjoy a guided experience{destination_phrase}, with local context and a clear route through the day’s main highlights."
    if "boat" in combined or "cruise" in combined or "canal" in combined:
        return f"See the area from the water, adding a scenic perspective to the day’s planned experience{destination_phrase}."
    return f"Enjoy a planned experience{destination_phrase}, adding a clear highlight to the day while keeping the wider itinerary easy to follow."
