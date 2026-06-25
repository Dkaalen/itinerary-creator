import hashlib
import json
from pathlib import Path

from scripts.golden_input_inventory import summarize_golden_inputs
from scripts.vipin_excel_corpus import evaluate_excel_corpus, load_items_jsonl

VIPIN_ITEMS_PATH = Path("tests/fixtures/real_inputs/vipin_nordic_calculator_corpus_items.jsonl")
VIPIN_MANIFEST_PATH = Path("tests/fixtures/real_inputs/vipin_nordic_calculator_corpus_manifest.json")


def _load_manifest():
    return json.loads(VIPIN_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_vipin_full_corpus_fixture_is_available_and_traceable():
    items = load_items_jsonl(VIPIN_ITEMS_PATH)
    manifest = _load_manifest()

    assert len(items) == 5557
    assert manifest["item_count"] == len(items)
    assert manifest["file_counts"] == {
        "Vipin Calculator Nordic 2.xlsx": 3616,
        "Vipin Nordic Calculator 3.xlsx": 1941,
    }
    assert len({(item.file, item.sheet) for item in items}) == 307
    assert manifest["sha256"] == hashlib.sha256(VIPIN_ITEMS_PATH.read_bytes()).hexdigest()


def test_vipin_full_corpus_inventory_counts_real_inputs():
    inventory = summarize_golden_inputs()

    assert inventory.vipin_item_count == 5557
    assert inventory.vipin_sheet_count == 307
    assert inventory.vipin_top_type_counts["transfer"] == 2001
    assert inventory.vipin_top_type_counts["activity"] == 1891
    assert inventory.real_input_files >= 17


def test_vipin_full_corpus_representative_sample_still_parses():
    items = load_items_jsonl(VIPIN_ITEMS_PATH)
    wanted_types = {"activity", "hotel", "transfer", "day overview", "leisure", "arrival"}
    sample = []
    seen = set()
    for item in items:
        key = (item.row_type or "").lower()
        if key not in wanted_types or key in seen:
            continue
        if not item.day or not item.element:
            continue
        sample.append(item)
        seen.add(key)
        if seen == wanted_types:
            break

    assert seen == wanted_types
    summary = evaluate_excel_corpus(sample, workers=1, chunk_size=3)

    assert summary["parse_errors"] == 0
    assert summary["parsed_count"] >= 5
    assert summary["bulk_generation_ok"] is True
