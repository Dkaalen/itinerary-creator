"""Validate IDs and cross-references in a structured itinerary document."""

from collections import Counter
from itinerary_generation.structured_model import ItineraryDocument,ModelWarning
from itinerary_generation.structured_validation_coverage import validate_duplicate_inclusion_sources,validate_exclusion_source_coverage,validate_inclusion_source_coverage
from itinerary_generation.structured_validation_support import status_is_included

def validate_itinerary_document(document:ItineraryDocument)->tuple[ModelWarning,...]:
    warnings=[];source_ids=[ref.row_id for ref in document.source_rows if ref.row_id];source_set=set(source_ids);item_ids=[item.item_id for item in document.items if item.item_id];item_set=set(item_ids)
    for row_id,count in Counter(source_ids).items():
        if count>1:warnings.append(ModelWarning("duplicate_source_row_id","Two normalized rows share the same source row id.","error",(row_id,)))
    for item_id,count in Counter(item_ids).items():
        if count>1:warnings.append(ModelWarning("duplicate_document_item_id","Two document items share the same item id.","error",(item_id,)))
    for item in document.items:
        missing=tuple(row_id for row_id in item.source_row_ids if row_id not in source_set)
        if missing:warnings.append(ModelWarning("item_missing_source_row","A document item references a source row that is not present in the document.","error",missing))
    for day in document.days:
        missing=tuple(item_id for item_id in day.item_ids if item_id not in item_set)
        if missing:warnings.append(ModelWarning("day_missing_document_item","A day references a document item that is not present in the document.","error",missing))
        missing=tuple(row_id for row_id in day.source_row_ids if row_id not in source_set)
        if missing:warnings.append(ModelWarning("day_missing_source_row","A day references a source row that is not present in the document.","error",missing))
    for section in (*document.inclusions,*document.exclusions):
        for item in section.items:
            missing=tuple(row_id for row_id in item.source_row_ids if row_id not in source_set)
            if missing:warnings.append(ModelWarning("structured_list_item_missing_source_row","A structured inclusion/exclusion item references a missing source row.","error",missing))
    linked={item_id for day in document.days for item_id in day.item_ids};unlinked=tuple(item.item_id for item in document.items if status_is_included(item.commercial_status) and item.item_id not in linked)
    if unlinked:warnings.append(ModelWarning("included_items_not_linked_to_day","Included document items are not linked from any day.","error",unlinked[:20]))
    warnings.extend(validate_inclusion_source_coverage(document));warnings.extend(validate_exclusion_source_coverage(document));warnings.extend(validate_duplicate_inclusion_sources(document))
    return tuple(dict.fromkeys(warnings))
