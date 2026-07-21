from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from calculator.library_model import LocalLibraryRow
from calculator.library_ranking import (
    LOCAL_LIBRARY_RANKING_SPEC,
    local_library_ranking_spec_payload,
    normalize_search_text,
)
from calculator.library_search import LocalLibrarySearchContext, search_library_rows

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "calculator_library_ranking_cases.json").read_text(encoding="utf-8"))
LIBRARY_JS = ROOT / "calculator_grid_component" / "frontend" / "js" / "calculator_grid_library.js"


def test_normalization_fixtures_follow_the_canonical_python_spec() -> None:
    for fixture in FIXTURES["normalization"]:
        assert normalize_search_text(fixture["input"]) == fixture["expected"]


def test_python_reference_ranking_matches_expected_fixture_order() -> None:
    for fixture in FIXTURES["ranking"]:
        rows = tuple(LocalLibraryRow(**row) for row in fixture["rows"])
        context = LocalLibrarySearchContext(**fixture["context"])
        results = search_library_rows(rows, fixture["query"], context=context, limit=len(rows))
        assert [result.row.library_id for result in results] == fixture["expected_ids"], fixture["name"]


def test_browser_and_python_ranking_share_normalization_scores_and_order() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is unavailable for browser-rule parity execution.")

    payload = {
        "spec": local_library_ranking_spec_payload(),
        "normalization": FIXTURES["normalization"],
        "ranking": FIXTURES["ranking"],
    }
    runner = r"""
const fs = require('fs');
const vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const source = fs.readFileSync(process.argv[1], 'utf8');
const sandbox = {
  console,
  DEFAULT_CURRENCY: 'EUR',
  numberValue: (value) => Number(value || 0),
  optionalNumberValue: (value) => value === null || value === undefined || value === '' ? null : Number(value)
};
vm.createContext(sandbox);
vm.runInContext(source, sandbox);
sandbox.__input = input;
const output = vm.runInContext(`(() => {
  const normalization = __input.normalization.map((fixture) => normalizeSearchText(fixture.input, __input.spec));
  const ranking = __input.ranking.map((fixture) => {
    const rows = fixture.rows.map((row) => prepareExpandedLibraryItem({...row, row_data: {...row}}, __input.spec));
    const index = buildLibrarySearchIndex(rows, __input.spec);
    return findLibrarySuggestions(rows, fixture.query, rows.length, fixture.context, index, __input.spec)
      .map((result) => ({id: result.item.library_id, score: result.score}));
  });
  return {normalization, ranking};
})()`, sandbox);
process.stdout.write(JSON.stringify(output));
"""
    completed = subprocess.run(
        [node, "-e", runner, str(LIBRARY_JS)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    browser_output = json.loads(completed.stdout)

    assert browser_output["normalization"] == [fixture["expected"] for fixture in FIXTURES["normalization"]]
    for fixture, browser_results in zip(FIXTURES["ranking"], browser_output["ranking"], strict=True):
        rows = tuple(LocalLibraryRow(**row) for row in fixture["rows"])
        context = LocalLibrarySearchContext(**fixture["context"])
        python_results = search_library_rows(rows, fixture["query"], context=context, limit=len(rows))
        assert browser_results == [
            {"id": result.row.library_id, "score": result.score}
            for result in python_results
        ], fixture["name"]


def test_ranking_payload_is_an_isolated_copy_of_the_canonical_spec() -> None:
    payload = local_library_ranking_spec_payload()
    assert payload == LOCAL_LIBRARY_RANKING_SPEC
    payload["version"] = "mutated"
    assert LOCAL_LIBRARY_RANKING_SPEC["version"] != "mutated"
