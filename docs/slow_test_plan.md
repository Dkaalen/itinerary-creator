# Slow test plan

The slow lane is intentionally isolated from instant health, fast, CI matrix,
and release candidate defaults.

Run it only when large fixture or PDF-heavy stability is part of the validation:

```powershell
python scripts/run_test_group.py slow
```

or together with release candidate validation:

```powershell
python scripts/run_release_candidate.py --include-slow
```

## Rules

- Each slow target runs in its own subprocess.
- The slow launcher uses a plain subprocess loop, not process exec-chaining, so a
  completed lane returns cleanly to CI/local runners.
- Timeouts fail honestly; they are not swallowed.
- The slow plan shown by `python scripts/run_test_group.py slow --plan` must match
  the direct slow harness.
- Slow checks should protect real high-risk behavior, not patch history.

Current slow modules are owned in `scripts/test_groups.py` through `SLOW_TESTS`
and direct split targets through `SLOW_TEST_SPLITS`.
