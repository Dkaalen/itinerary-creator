from __future__ import annotations

import re
from pathlib import Path


FRONTEND = Path("calculator_grid_component/frontend")
JS = FRONTEND / "js"


def _source(name: str) -> str:
    return (JS / name).read_text(encoding="utf-8")


def test_calculator_namespace_loads_before_namespaced_modules() -> None:
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    namespace = 'js/calculator_grid_namespace.js'
    storage = 'js/calculator_grid_storage_core.js'
    library = 'js/calculator_grid_library_normalization.js'

    assert namespace in index
    assert index.index(namespace) < index.index(storage)
    assert index.index(namespace) < index.index(library)
    assert "window.ItineraryCalculator" in _source("calculator_grid_namespace.js")
    assert "function define(" in _source("calculator_grid_namespace.js")
    assert "function requireModule(" in _source("calculator_grid_namespace.js")


def test_split_storage_and_library_modules_do_not_declare_global_functions() -> None:
    split_modules = (
        "calculator_grid_storage_core.js",
        "calculator_grid_draft_repository.js",
        "calculator_grid_recovery_repository.js",
        "calculator_grid_library_normalization.js",
        "calculator_grid_library_transport.js",
        "calculator_grid_library_index.js",
        "calculator_grid_library_search.js",
        "calculator_grid_library_selection.js",
    )
    for filename in split_modules:
        source = _source(filename)
        assert source.lstrip().startswith("//")
        assert "(() => {" in source
        assert re.search(r"^function\s+", source, flags=re.MULTILINE) is None, filename
        assert "window.ItineraryCalculator.define(" in source


def test_storage_public_api_is_explicit_and_callers_use_it() -> None:
    facade = _source("calculator_grid_storage_api.js")
    controller = _source("calculator_grid_state_controller.js")
    protocol = _source("calculator_grid_protocol.js")
    actions = _source("calculator_grid_actions.js")

    assert "window.ItineraryCalculator.publish('storage'" in facade
    assert "storage.setDraftStorageKey" in controller
    assert "storage.saveDraft" in controller
    assert "storage.clearDraft" in protocol
    assert "storage.restoreRecoverySnapshot" in actions
    assert "function saveCalculatorDraft(" not in facade
    assert "function restoreCalculatorRecoverySnapshot(" not in facade


def test_library_public_api_is_explicit_and_callers_use_it() -> None:
    facade = _source("calculator_grid_library_api.js")
    controller = _source("calculator_grid_state_controller.js")
    suggestions = _source("calculator_grid_suggestions.js")

    assert "window.ItineraryCalculator.publish('library'" in facade
    assert "library.prepareBundle(payload)" in controller
    assert "library.findSuggestions(" in suggestions
    assert "library.applySuggestion(" in suggestions
    assert "function findLibrarySuggestions(" not in facade
    assert "function applyLibrarySuggestion(" not in facade


def test_large_multi_domain_frontend_owners_were_split() -> None:
    draft_facade_lines = len(_source("calculator_grid_storage_api.js").splitlines())
    library_facade_lines = len(_source("calculator_grid_library_api.js").splitlines())

    assert draft_facade_lines < 50
    assert library_facade_lines < 60
    assert (JS / "calculator_grid_draft_repository.js").exists()
    assert (JS / "calculator_grid_recovery_repository.js").exists()
    assert (JS / "calculator_grid_library_search.js").exists()
    assert (JS / "calculator_grid_library_transport.js").exists()
    assert not (JS / "calculator_grid_draft_storage.js").exists()
    assert not (JS / "calculator_grid_library.js").exists()


def test_namespaced_modules_add_no_accidental_window_globals() -> None:
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        return
    files = (
        "calculator_grid_namespace.js",
        "calculator_grid_library_normalization.js",
        "calculator_grid_library_transport.js",
        "calculator_grid_library_index.js",
        "calculator_grid_library_search.js",
        "calculator_grid_library_selection.js",
        "calculator_grid_library_api.js",
        "calculator_grid_storage_core.js",
        "calculator_grid_draft_repository.js",
        "calculator_grid_recovery_repository.js",
        "calculator_grid_storage_api.js",
    )
    runner = r"""
const fs = require('fs');
const vm = require('vm');
const sandbox = {console};
sandbox.window = sandbox;
const before = new Set(Object.keys(sandbox));
vm.createContext(sandbox);
for (const path of process.argv.slice(1)) vm.runInContext(fs.readFileSync(path, 'utf8'), sandbox);
const added = Object.keys(sandbox).filter((key) => !before.has(key));
const namespace = sandbox.ItineraryCalculator;
let duplicateRejected = false;
try { namespace.define('library.index', {}); } catch (_error) { duplicateRejected = true; }
process.stdout.write(JSON.stringify({
  added,
  duplicateRejected,
  hasLibrary: Boolean(namespace.library),
  hasStorage: Boolean(namespace.storage),
}));
"""
    completed = subprocess.run(
        [node, "-e", runner, *(str(JS / name) for name in files)],
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    result = json.loads(completed.stdout)
    assert result == {
        "added": ["ItineraryCalculator"],
        "duplicateRejected": True,
        "hasLibrary": True,
        "hasStorage": True,
    }
