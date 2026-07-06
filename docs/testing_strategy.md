# Test strategy

## Current confidence hierarchy

1. Quick health check: `python scripts/run_health_check.py`
2. Fast behavior lane: `python scripts/run_test_group.py fast`
3. Focused lane: `python scripts/run_test_group.py <group>`
4. Release candidate: `python scripts/run_release_candidate.py`
5. Optional isolated slow lane: `python scripts/run_release_candidate.py --include-slow`
6. Full discovery fallback: `python scripts/run_test_group.py full`

Raw `python -m pytest` is no longer the main confidence path. The suite is too
large and uneven for a single opaque command to be the daily gate.

## Group rules

- `fast` must stay free of PDF, slow, and large quality modules.
- `pdf` owns rendering/parity checks that can touch ReportLab or generated PDFs.
- `quality` owns broader content and generated-output regressions.
- `slow` owns large fixture and PDF-heavy stability checks and runs by direct
  process isolation.
- Product lanes (`calculator`, `storage`, `parser`, `images`, `ui`, `workflow`,
  etc.) should prove behavior for that domain, not patch history.

## Marker rules

Pytest markers are applied from `tests/conftest.py` using the shared group source
of truth in `scripts/test_groups.py`. Do not manually duplicate marker lists in
random test files.

Every runner group has a matching pytest marker so targeted collection remains
possible. Coarse markers are also applied:

- `unit` for fast-lane modules
- `integration` for grouped non-fast modules
- `pdf`, `quality`, and `slow` for intentionally heavier checks

## Cleanup priorities

Static audit command:

```powershell
python scripts/test_suite_audit.py
```

Use the audit report to drive future cleanup. Highest-value cleanup areas are:

1. Replace source-string tests with behavior tests where practical.
2. Rename patch-history filenames only when it improves discoverability.
3. Keep slow/PDF/image-heavy tests isolated from fast and CI matrix lanes.
4. Consolidate fixtures locally by domain, not through one giant `conftest.py`.
5. Add high-value regressions only for product risks that can break the hosted app.
