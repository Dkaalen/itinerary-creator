"""Presentation-layer language labels for itinerary output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_PRESENTATION_LANGUAGE = "en"

SUPPORTED_PRESENTATION_LANGUAGES: dict[str, str] = {
    "en": "English",
    "no": "Norwegian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
}

_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "travel_itinerary": "Travel Itinerary",
        "route": "Route",
        "trip_glance": "Your Trip at a Glance",
        "journey_arc": "How Your Trip Unfolds",
        "chapter": "Chapter",
        "days": "Days",
        "experience": "What You’ll Experience",
        "whats_included": "What’s included",
        "whats_not_included": "What’s not included",
        "important_travel_notes": "Important travel notes",
        "optional_experiences": "Optional Experiences",
        "day": "DAY",
        "included_tour_day": "Included on This Tour Day",
        "included_experience": "Included With This Experience",
        "description": "Description",
        "notable_sights": "Notable Sights",
        "includes": "Includes",
    },
    "no": {
        "travel_itinerary": "Reiseprogram",
        "route": "Rute",
        "trip_glance": "Reisen i korte trekk",
        "journey_arc": "Reisens hovedlinje",
        "chapter": "Kapittel",
        "days": "Dager",
        "experience": "Opplevelser",
        "whats_included": "Dette er inkludert",
        "whats_not_included": "Dette er ikke inkludert",
        "important_travel_notes": "Viktige reisenotater",
        "optional_experiences": "Valgfrie opplevelser",
        "day": "DAG",
        "included_tour_day": "Inkludert denne turdagen",
        "included_experience": "Inkludert i opplevelsen",
        "description": "Beskrivelse",
        "notable_sights": "Høydepunkter",
        "includes": "Inkluderer",
    },
    "de": {
        "travel_itinerary": "Reiseverlauf",
        "route": "Route",
        "trip_glance": "Ihre Reise auf einen Blick",
        "journey_arc": "Reiseverlauf im Überblick",
        "chapter": "Kapitel",
        "days": "Tage",
        "experience": "Was Sie erleben",
        "whats_included": "Inbegriffen",
        "whats_not_included": "Nicht inbegriffen",
        "important_travel_notes": "Wichtige Reisehinweise",
        "optional_experiences": "Optionale Erlebnisse",
        "day": "TAG",
        "included_tour_day": "An diesem Reisetag inbegriffen",
        "included_experience": "Bei diesem Erlebnis inbegriffen",
        "description": "Beschreibung",
        "notable_sights": "Sehenswürdigkeiten",
        "includes": "Enthält",
    },
    "fr": {
        "travel_itinerary": "Itinéraire de voyage",
        "route": "Parcours",
        "trip_glance": "Votre voyage en un coup d’œil",
        "journey_arc": "Fil conducteur du voyage",
        "chapter": "Chapitre",
        "days": "Jours",
        "experience": "Ce que vous vivrez",
        "whats_included": "Ce qui est inclus",
        "whats_not_included": "Ce qui n’est pas inclus",
        "important_travel_notes": "Notes de voyage importantes",
        "optional_experiences": "Expériences optionnelles",
        "day": "JOUR",
        "included_tour_day": "Inclus pour cette journée",
        "included_experience": "Inclus dans cette expérience",
        "description": "Description",
        "notable_sights": "Sites remarquables",
        "includes": "Comprend",
    },
    "es": {
        "travel_itinerary": "Itinerario de viaje",
        "route": "Ruta",
        "trip_glance": "Tu viaje de un vistazo",
        "journey_arc": "Resumen del viaje",
        "chapter": "Capítulo",
        "days": "Días",
        "experience": "Qué experimentarás",
        "whats_included": "Qué está incluido",
        "whats_not_included": "Qué no está incluido",
        "important_travel_notes": "Notas importantes de viaje",
        "optional_experiences": "Experiencias opcionales",
        "day": "DÍA",
        "included_tour_day": "Incluido en este día de tour",
        "included_experience": "Incluido en esta experiencia",
        "description": "Descripción",
        "notable_sights": "Lugares destacados",
        "includes": "Incluye",
    },
}


@dataclass(frozen=True, slots=True)
class PresentationLabels:
    language: str
    labels: dict[str, str]

    def label(self, key: str, fallback: str = "") -> str:
        return str(self.labels.get(key) or _LABELS[DEFAULT_PRESENTATION_LANGUAGE].get(key) or fallback or key)


def normalize_presentation_language(value: Any) -> str:
    code = str(value or DEFAULT_PRESENTATION_LANGUAGE).strip().lower()
    if code in SUPPORTED_PRESENTATION_LANGUAGES:
        return code
    return DEFAULT_PRESENTATION_LANGUAGE


def presentation_language_from_output_edits(output_edits: Mapping[str, Any] | None) -> str:
    return normalize_presentation_language((output_edits or {}).get("presentation_language"))


def presentation_labels(language: Any = DEFAULT_PRESENTATION_LANGUAGE) -> PresentationLabels:
    code = normalize_presentation_language(language)
    base = dict(_LABELS[DEFAULT_PRESENTATION_LANGUAGE])
    base.update(_LABELS.get(code, {}))
    return PresentationLabels(language=code, labels=base)


def label_for(output_edits: Mapping[str, Any] | None, key: str, fallback: str = "") -> str:
    return presentation_labels(presentation_language_from_output_edits(output_edits)).label(key, fallback)


__all__ = [
    "DEFAULT_PRESENTATION_LANGUAGE",
    "SUPPORTED_PRESENTATION_LANGUAGES",
    "PresentationLabels",
    "label_for",
    "normalize_presentation_language",
    "presentation_labels",
    "presentation_language_from_output_edits",
]
