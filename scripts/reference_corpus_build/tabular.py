"""Build standard-template and clean-activity TSV corpora."""

import re
from pathlib import Path
from scripts.reference_corpus_build.common import canonical_place, read_three_column_source, write_tsv

PLACEHOLDER_RE = re.compile(r"\[([^\[\]]+)\]")
CONDITIONAL_MARKERS = ("if snow", "weather permitting", "depending on weather", "subject to weather", "not guaranteed", "upon request", "on request", "if needed", "where included", "subject to availability")


def build_standard_templates(source_path: Path, output_path: Path) -> int:
    output = []
    for index, (service_type, destination, text) in enumerate(read_three_column_source(source_path), start=1):
        output.append({"record_id": f"standard-{index:04d}", "service_type": service_type, "source_destination": destination, "canonical_destination": canonical_place(destination), "template_text": text, "placeholders": ";".join(sorted({item.strip() for item in PLACEHOLDER_RE.findall(text)}))})
    write_tsv(output_path, ("record_id", "service_type", "source_destination", "canonical_destination", "placeholders", "template_text"), output)
    return len(output)


def build_clean_activities(source_path: Path, output_path: Path) -> int:
    output = []
    for index, (record_type, city, text) in enumerate(read_three_column_source(source_path), start=1):
        prefix, separator, _ = text.partition(":"); location = prefix.strip() if separator else ""; lower = text.lower()
        output.append({"record_id": f"activity-{index:04d}", "record_type": record_type, "source_city": city, "canonical_city": canonical_place(city), "activity_location": location, "canonical_activity_location": canonical_place(location), "activity_text": text, "conditional_markers": ";".join(marker for marker in CONDITIONAL_MARKERS if marker in lower)})
    write_tsv(output_path, ("record_id", "record_type", "source_city", "canonical_city", "activity_location", "canonical_activity_location", "conditional_markers", "activity_text"), output)
    return len(output)
