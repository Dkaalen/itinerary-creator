"""Quality validation for canonical/generated itinerary content.

This module is deliberately pessimistic.  It is used by tests and tooling to
catch raw supplier/admin fragments before a patch is considered shippable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    ("mechanical_day_intro", r"\bThe arrangements in\b"),
    ("opening_hours_in_title", r"Opening Hours\s*:"),
    ("misspelled_includes", r"\bIncludese\b"),
    ("bad_ticket_case", r"(?-i:\bTIckets\b)"),
    ("misspelled_excursion", r"(?-i:\bExcurssion\b)"),
    ("raw_tickets_included", r"Tickets Included\s*:"),
    ("bad_fractional_duration_spacing", r"\b2\.\s+5\s*hr\b"),
    ("raw_leisure_title", r"\bLeisure as requested\b"),
    ("raw_accommodation_prefix", r"Accommodation\s*:\s*Check[- ]?in at"),
    ("duplicate_departure_home", r"\bDeparture home\b"),
    ("cost_not_included_leak", r"\bCost not included\b"),
    ("self_arranged_raw_case", r"\bSelf Arranged\b"),
    ("old_breakfast_wording", r"\bWith breakfast\b"),
    ("supplier_operation_carried_out", r"\bCarried out\s*:"),
    ("supplier_operation_participanter", r"\bParticipanter\b"),
    ("broken_train_fragment", r"s compartment Overnight Train"),
    ("car_drive_destination", r"\bCAR\s*·\s*DRIVE\b"),
    ("standalone_local_bullet", r"<li>\s*Local\s*</li>"),
    ("standalone_experienced_bullet", r"<li>\s*Experienced\s*</li>"),
    ("split_personal_experience_bullet", r"<li>\s*Personal experience\s*</li>"),
    ("fløibanen_bad_duration", r"Fløibanen[\s\S]{0,500}Duration:</span>\s*5[–-]8 minutes"),
    ("internal_icebreaker_note", r"There are 2 options in Icebreaker"),
    ("supplier_hype_instagram", r"\bInstagram account pop\b"),
    ("supplier_call_to_action", r"\bCome and join us\b|\bWhat are you waiting for\b|\bStart your adventure\b|\bBook today\b|\bCheck availability\b"),
    ("raw_group_tour_supplier_phrase", r"\bPrepare to explore amazing things\b|\bThirsty\?\b|\binstant foot wetness\b"),
    ("generic_day_intro_planned_highlight", r"\bA planned highlight brings you into\b"),
    ("generic_day_intro_main_experience", r"\bYour main experience today is\b"),
    ("generic_day_intro_shaped_around", r"\bThe day is shaped around\b"),
    ("generic_focus_phrase", r"\bgives the day a clear focus\b|\boffering a well-paced way\b"),
    ("raw_supplier_brand_in_description", r"Enjoy Secret Food Tours\b"),
    ("raw_pls", r"\bPls\b|\bplz\b"),
    ("raw_addon_cost", r"\baddon cost\b|\bpaid on ground\b"),
    ("raw_transport_typo", r"\btranfers\b|\brelased\b|\bDate dependant\b|\bFight\s*:"),
    ("raw_private_transfer_shorthand", r"\bPrivate Hotel to\b|\bPrivate Airport to\b|\bPrivate Station to\b|\bPrivate Bustation to\b"),
    ("raw_self_transfer_case", r"(?-i:\bself Transfer\b|\bSelf Transfer\b)"),
    ("terminal_as_destination_case", r"(?-i:\blevi Bus Station\b|\brovaniemi Bus Station\b)"),
    ("voucher_as_destination", r"be shared in Voucher"),
    ("voucher_admin_title", r"\b(?:Final timing|Train|Timing|Time|Details?) to be shared in Voucher\b"),
    ("wrong_stockholm_tallinn", r"Stockholm[\s\S]{0,900}Tallinn Old Town"),
    ("wrong_oslo_danish_food", r"Oslo[\s\S]{0,900}(?:smørrebrød|Danish meatballs)"),
    ("oslofjord_hike_water_based", r"Oslofjord Nature Hike[\s\S]{0,900}water-based"),
    ("equipment_as_description_focus", r"experience focused on (?:Helmet|Duration|Warm blankets|Private vehicle|Aksla Viewpoint)"),
    ("hop_on_main_title", r'<div class="day-title">Hop[- ]on hop[- ]off'),
    ("empty_city_activity_title", r'<div class="day-title">Copenhagen</div>'),
    ("group_title_today_artifact", r"(?:Ice Cave|Local Life) Today"),
]


# These checks are valid only inside a coherent day/activity section. Running
# them against the whole document can falsely connect an Oslo hotel in final
# inclusions with a Copenhagen food tour several sections later.
SCOPED_FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    ("wrong_stockholm_tallinn", r"Stockholm[\s\S]{0,900}Tallinn Old Town"),
    ("wrong_oslo_danish_food", r"Oslo[\s\S]{0,900}(?:smørrebrød|Danish meatballs)"),
    ("oslofjord_hike_water_based", r"Oslofjord Nature Hike[\s\S]{0,900}water-based"),
    ("fløibanen_bad_duration", r"Fløibanen[\s\S]{0,500}Duration:</span>\s*5[–-]8 minutes"),
]


_SCOPED_FORBIDDEN_CODES = {code for code, _ in SCOPED_FORBIDDEN_PATTERNS}


@dataclass(slots=True)
class QualityFinding:
    code: str
    message: str
    context: str = ""


@dataclass(slots=True)
class FixtureQualityReport:
    fixture_name: str
    day_count: int
    row_count: int
    findings: list[QualityFinding] = field(default_factory=list)
    day_summaries: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings


def _strip_heavy_assets(value: str) -> str:
    """Remove embedded image/style payloads before text validation.

    Fixture checks validate itinerary wording, not binary image data.  The app
    preview embeds cover/day imagery as long data URIs, which can make repeated
    regex scans extremely slow and, worse, hide real content issues behind test
    timeouts.  Keep the semantic HTML and remove only payload-heavy attributes.
    """
    text = str(value or "")
    text = re.sub(r'url\("data:image/[^"\)]*"\)', 'url("")', text, flags=re.IGNORECASE)
    text = re.sub(r'src="data:image/[^"]*"', 'src=""', text, flags=re.IGNORECASE)
    text = re.sub(r'--cover-bg-image:\s*url\("[^"]*"\);', '--cover-bg-image: url("");', text, flags=re.IGNORECASE)
    return text


def compact_html(value: str) -> str:
    lean = _strip_heavy_assets(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", lean)
    text = text.replace("&amp;", "&").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def validate_html(html: str) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    lean_html = _strip_heavy_assets(html)
    plain = compact_html(lean_html)
    for code, pattern in FORBIDDEN_PATTERNS:
        if code in _SCOPED_FORBIDDEN_CODES:
            continue
        target = lean_html if "<" in pattern else plain
        match = re.search(pattern, target, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 80)
            end = min(len(target), match.end() + 120)
            findings.append(QualityFinding(code, f"Forbidden pattern matched: {code}", target[start:end]))

    for section_match in re.finditer(r'<section class="day-section"[^>]*>[\s\S]*?</section>', lean_html, flags=re.IGNORECASE):
        section_html = section_match.group(0)
        section_plain = compact_html(section_html)
        for code, pattern in SCOPED_FORBIDDEN_PATTERNS:
            target = section_html if "<" in pattern else section_plain
            match = re.search(pattern, target, flags=re.IGNORECASE)
            if match:
                start = max(0, match.start() - 80)
                end = min(len(target), match.end() + 120)
                findings.append(QualityFinding(code, f"Forbidden pattern matched in day section: {code}", target[start:end]))
    return findings


def extract_day_summaries(html: str) -> list[str]:
    summaries: list[str] = []
    lean_html = _strip_heavy_assets(html)
    for match in re.finditer(r'<section class="day-section" data-day="([^"]+)">([\s\S]*?)</section>', lean_html):
        day = match.group(1)
        body = match.group(2)
        title_match = re.search(r'<div class="day-title">([\s\S]*?)</div>', body)
        intro_match = re.search(r'<div class="intro">([\s\S]*?)</div>', body)
        desc_matches = re.findall(r'<div class="section-title small-section">Description</div>\s*<div class="body-text muted-note">([\s\S]*?)</div>', body)
        activity_titles = re.findall(r'<div class="content-block activity-block"[\s\S]*?<div class="body-text strong-line">([\s\S]*?)</div>', body)
        transport_lines = re.findall(r'<div class="content-block travel-sequence-block">[\s\S]*?<li>([\s\S]*?)</li>', body)
        route_lines = re.findall(r'<div class="content-block day-overview-block"[\s\S]*?<li>([\s\S]*?)</li>', body)
        title = compact_html(title_match.group(1) if title_match else "")
        intro = compact_html(intro_match.group(1) if intro_match else "")
        desc = " | ".join(compact_html(item) for item in desc_matches[:2])
        acts = ", ".join(compact_html(item) for item in activity_titles[:3])
        transports = ", ".join(compact_html(item) for item in transport_lines[:3])
        routes = ", ".join(compact_html(item) for item in route_lines[:3])
        summaries.append(
            f"{day}: title={title!r}; intro={intro[:100]!r}; "
            f"activities={acts[:140]!r}; descriptions={desc[:140]!r}; "
            f"transport={transports[:140]!r}; routes={routes[:140]!r}"
        )
    return summaries
