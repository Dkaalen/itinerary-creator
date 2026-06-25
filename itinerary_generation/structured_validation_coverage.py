"""Validate source-aware inclusion and exclusion coverage."""

from itinerary_generation.structured_model import ItineraryDocument,ModelWarning
from itinerary_generation.structured_validation_support import REVIEW_KIND_COVERAGE,SOURCE_SIGNAL_GROUPS,compact_tokens,item_identity_text,list_items_by_source,source_requires_exclusion,source_text,status_is_included

def validate_inclusion_source_coverage(document:ItineraryDocument)->list[ModelWarning]:
    warnings=[];sources={source.row_id:source for source in document.source_rows if source.row_id};mapping=list_items_by_source(document.inclusions)
    for item in document.items:
        if item.kind not in REVIEW_KIND_COVERAGE or not status_is_included(item.commercial_status) or not str(item.title or "").strip() or str(item.title).strip().lower()=="untitled item":continue
        for row_id in item.source_row_ids:
            if not row_id:continue
            inclusion_items=mapping.get(row_id,[])
            if not inclusion_items:warnings.append(ModelWarning("included_item_missing_inclusion_coverage","An included activity/accommodation item is linked to a day but has no matching source-aware inclusion item.","warning",(row_id,)));continue
            source=source_text(sources.get(row_id));support=compact_tokens("\n".join((source,item_identity_text(item))));source_tokens=compact_tokens(source)
            for inclusion in inclusion_items:
                label="\n".join((inclusion.label,*inclusion.detail_lines));label_tokens=compact_tokens(label)
                if len(label_tokens)>=2 and len(support)>=2 and label_tokens.isdisjoint(support):warnings.append(ModelWarning("inclusion_label_not_supported_by_source","An inclusion label has little overlap with its linked source row; review for possible title contamination from another product.","warning",(row_id,)))
                if len(label_tokens)>=2 and len(source_tokens)>=2 and label_tokens.isdisjoint(source_tokens):warnings.append(ModelWarning("inclusion_label_inferred_from_weak_source","An inclusion label is not directly supported by the supplier/source row text; confirm the product name before final output.","warning",(row_id,)))
                lower_source,lower_label=source.lower(),label.lower()
                if any(any(signal in lower_source for signal in group) and not any(signal in lower_label for signal in group) for group in SOURCE_SIGNAL_GROUPS):warnings.append(ModelWarning("inclusion_source_signal_missing_from_label","An activity inclusion label appears to have lost an important source-row signal; review for possible cross-row merge or overwritten title.","warning",(row_id,)))
    return warnings

def validate_exclusion_source_coverage(document:ItineraryDocument)->list[ModelWarning]:
    mapping=list_items_by_source(document.exclusions)
    return [ModelWarning("commercial_row_missing_exclusion_coverage","A self-arranged, optional or cost-not-included source row is not linked to a structured What's-not-included item.","warning",(source.row_id,)) for source in document.source_rows if source.row_id and source_requires_exclusion(source) and not mapping.get(source.row_id)]

def validate_duplicate_inclusion_sources(document:ItineraryDocument)->list[ModelWarning]:
    warnings=[];seen=set()
    for section in document.inclusions:
        for item in section.items:
            label=" ".join(str(item.label or "").lower().split())
            if not label:continue
            for row_id in item.source_row_ids:
                key=(row_id,label)
                if key in seen:warnings.append(ModelWarning("duplicate_inclusion_for_source_row","A source row produced the same inclusion label more than once.","warning",(row_id,)))
                seen.add(key)
    return warnings
