"""Coordinate row normalization and itinerary-level contextual enrichment."""

from normalizer_modules.context import add_repeated_activity_context,apply_contextual_travel_corrections,fill_missing_context_cities
from normalizer_modules.rental import looks_like_rental_vehicle_row as _looks_like_rental_vehicle_row,normalize_rental_vehicle_row as _normalize_rental_vehicle_row
from normalizer_modules.row_classification import looks_like_misclassified_hotel_row as _looks_like_misclassified_hotel_row,warn_suspicious_city
from normalizer_modules.row_normalizer import normalize_row,protect_hotel_owned_text as _protect_hotel_owned_text
from itinerary_domain.group_tour_parsing import integrate_group_tour_rows,prepare_group_tour_source_rows
from itinerary_domain.group_tour_optional_extras import annotate_group_tour_optional_extras

_fill_missing_context_cities=fill_missing_context_cities

def normalize_itinerary_rows(rows:list[dict],*,source_name:str="",group_tour_season:str="")->list[dict]:
    normalized=[normalize_row(row) for row in prepare_group_tour_source_rows(rows or [],source_name=source_name)]
    normalized=fill_missing_context_cities(normalized);normalized=apply_contextual_travel_corrections(normalized);normalized=add_repeated_activity_context(normalized);normalized=annotate_group_tour_optional_extras(normalized)
    return integrate_group_tour_rows(normalized,season=group_tour_season,source_name=source_name)

__all__=["normalize_row","normalize_itinerary_rows","warn_suspicious_city"]
