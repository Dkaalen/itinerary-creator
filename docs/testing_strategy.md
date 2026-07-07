# Test strategy

## Confidence hierarchy

1. Instant health check: `python scripts/run_health_check.py`
2. Critical product smoke lane: `python scripts/run_test_group.py critical`
3. Fast behavior lane: `python scripts/run_test_group.py fast`
4. Focused product lane: `python scripts/run_test_group.py <group>`
5. Release candidate: `python scripts/run_release_candidate.py`
6. Optional isolated slow lane: `python scripts/run_release_candidate.py --include-slow`
7. Full discovery fallback: `python scripts/run_test_group.py full`

Raw `python -m pytest` is not the main confidence path. The suite is too large
and uneven for one opaque command to be the daily gate.

## Instant health rules

The instant health check is deliberately small. It should run constantly during
patch work and catch the failure class where a major hosted-app feature silently
disappears, disconnects, or starts reusing stale state.

It currently runs:

- Python compile check
- production import smoke
- architecture guards
- critical product smoke lane
- runner/CI/marker guard tests

It does not run collect-only, static audit, PDF rendering, image-heavy checks, or
large real fixtures. Those belong to release or slow lanes.

## Critical lane rules

`critical` protects app surfaces and failure classes, not one named bug. It must
stay near-instant and should cover critical workflow wiring across the app:

- input/edit/pictures/export routing
- calculator and Local Library reachability
- parser-to-model contract
- calculator-to-XLSX contract
- saved-project identity and snapshots
- cloud open/list/delete safe behavior
- image review state transitions
- PDF stale-artifact invalidation after image changes
- frontend asset presence for custom components

Critical tests should be behavior or contract tests. They must not render PDFs,
process large fixture banks, inspect visual details exhaustively, or lock in
implementation source strings.

## Group rules

- `critical` is the always-run product smoke shield.
- `fast` is the small everyday behavior lane, free of PDF, slow, large quality,
  and implementation source-contract tests.
- `pdf` owns rendering/parity checks that can touch ReportLab or generated PDFs.
- `quality` owns broader content and generated-output regressions.
- `slow` owns large fixture and PDF-heavy stability checks and runs by direct
  subprocess isolation without exec-chaining.
- Product lanes (`calculator`, `storage`, `parser`, `images`, `ui`, `workflow`,
  etc.) should prove behavior for that domain, not patch history.

## Release candidate rules

`python scripts/run_release_candidate.py` is the strong pre-push gate. It runs
instant health, pytest collection, the static suite audit, all timeout-safe
product groups, frontend JavaScript syntax checks, and `git diff --check`.

The release group is deliberately split into small staged subprocesses. Parser,
activity, architecture, calculator, editor, image, UI, quality, and PDF lanes are
chunked so one wide group cannot hide progress, hang without context, or consume
the whole validation timeout. Each external release step has an honest timeout.

Use `--include-slow` only when large real-fixture/PDF stability checks are
intentionally part of the validation. Use `--skip-node` only when Node.js is not
available in a local environment.

## Marker rules

Pytest markers are applied from `tests/conftest.py` using the shared group source
of truth in `scripts/test_groups.py`. Do not manually duplicate marker lists in
random test files.

Every runner group has a matching pytest marker so targeted collection remains
possible. Coarse markers are also applied:

- `unit` for critical and fast-lane modules
- `integration` for grouped non-fast modules
- `pdf`, `quality`, and `slow` for intentionally heavier checks

## Audit rules

Static audit command:

```powershell
python scripts/test_suite_audit.py
```

The audit separates three different string-check categories:

- raw implementation source-contract assertions, which should stay at zero
- explicit static-contract helpers for unavoidable wiring/frontend/source guards
- generated-output text assertions, which are usually real product behavior

Prefer behavior tests. When a static guard is the right tradeoff, use
`tests.support.static_contracts` so the test is explicit about inspecting source
or frontend assets instead of hiding brittle `read_text()` assertions inside the
test body.

Legacy patch-history filenames and numbered patch-style test names should stay at
zero. Regression files should be named after the product behavior or domain they
protect.

Highest-value cleanup areas remain:

1. Convert explicit static-contract helper tests into behavior tests when practical.
2. Keep slow/PDF/image-heavy tests isolated from instant and CI matrix lanes.
3. Consolidate fixtures locally by domain, not through one giant `conftest.py`.
4. Add high-value regressions only for product risks that can break the hosted app.
