# Resumable test runner

The repository has one executable test manifest for named groups, the full
suite, and the compact release proof. Every stage has its own timeout, log,
checkpoint record, and duration history entry.

## Everyday commands

```powershell
python scripts/run_test_plan.py --plan fast
python scripts/run_test_plan.py --plan release --resume
python scripts/run_test_plan.py --plan full --resume
```

Equivalent positional group commands remain supported:

```powershell
python scripts/run_test_group.py full --resume
.\scripts\run_full_tests.ps1 --resume
```

## Recovering after a sandbox interruption

Run the same plan again with `--resume`. Stages with a checkpointed `PASS` are
skipped. A stage left as `RUNNING`, `FAIL`, or `TIMEOUT` is executed again.

```powershell
python scripts/run_test_plan.py --plan full --resume
```

Useful controls:

```powershell
python scripts/run_test_plan.py --plan full --show-plan
python scripts/run_test_plan.py --plan full --start-stage 43
python scripts/run_test_plan.py --plan full --stage-range 43:60
python scripts/run_test_plan.py --plan full --reset
python scripts/run_test_plan.py --plan full --no-fail-fast
```

## Test-run evidence

Local evidence is written under `.test-runs/` and is intentionally ignored by
Git:

```text
.test-runs/
  duration_history.jsonl
  full/
    checkpoint.json
    summary.json
    logs/
      001-fast-safety-....log
```

`checkpoint.json` is written atomically after a stage starts and after it
finishes. `summary.json` always distinguishes `PASS`, `FAIL`, `TIMEOUT`,
`RUNNING`, and `NOT_RUN`.

## Timeout diagnostics

Pytest stages run through `scripts/run_pytest_stage.py`. The worker enables
Python faulthandler and schedules an all-thread traceback shortly before the
hard stage limit. Output is streamed to the console and stage log. Silent
stages emit a heartbeat every 20 seconds by default.

Timeouts terminate the complete subprocess tree. If the outer sandbox kills
the orchestrator, its signal handler also terminates the active stage before
exiting, leaving the checkpoint safe to resume.

Timeout classes can be adjusted without changing the manifest:

```powershell
$env:ITINERARY_TEST_FAST_TIMEOUT_SECONDS = "180"
$env:ITINERARY_TEST_QUALITY_TIMEOUT_SECONDS = "360"
$env:ITINERARY_TEST_RENDER_TIMEOUT_SECONDS = "600"
$env:ITINERARY_TEST_SLOW_TIMEOUT_SECONDS = "180"
$env:ITINERARY_TEST_HEARTBEAT_SECONDS = "20"
```

## Duration baselines

Successful stage durations are appended to
`.test-runs/duration_history.jsonl`. A stage is flagged when it takes at least
twice its prior median and is at least ten seconds slower. The manifest
fingerprint ensures timings are compared only with the same stage definition.

## Release proof

The proof no longer owns a separate command list. It consumes the same central
manifest and resume/checkpoint implementation:

```powershell
python scripts/run_validation_proof.py --resume
python scripts/run_test_plan.py --plan proof --resume
```
