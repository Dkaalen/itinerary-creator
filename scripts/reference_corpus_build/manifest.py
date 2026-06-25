"""Build a checksummed reference-corpus manifest."""

import json
from pathlib import Path
from scripts.reference_corpus_build.common import CORPUS_VERSION, SCHEMA_VERSION, sha256


def build_manifest(output_dir: Path, *, standard_source: Path, activity_source: Path, iceland_source: Path, standard_count: int, activity_count: int, iceland_sheet_count: int, iceland_row_count: int) -> None:
    files = {"standard_input_templates.tsv": standard_count, "clean_activity_inputs.tsv": activity_count, "iceland_standard_itinerary.json": iceland_row_count}
    payload = {"schema_version": SCHEMA_VERSION, "corpus_version": CORPUS_VERSION, "files": [{"name": name, "record_count": count, "sha256": sha256(output_dir / name)} for name,count in files.items()], "source_files": [{"name": source.name, "sha256": sha256(source)} for source in (standard_source, activity_source, iceland_source)], "iceland_sheet_count": iceland_sheet_count}
    (output_dir / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
