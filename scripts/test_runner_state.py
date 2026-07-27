"""Checkpoint, history, and atomic state persistence for test plans."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from scripts.test_group_catalog import TEST_STAGE_BOUNDARY_SECONDS
from scripts.test_runner_models import StageRunResult, TestPlanSpec, TestStageSpec

STATE_SCHEMA_VERSION = 2
DEFAULT_STATE_ROOT_NAME = ".test-runs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def plan_state_dir(state_root: Path, plan_name: str) -> Path:
    return state_root / plan_name


def checkpoint_path(state_root: Path, plan_name: str) -> Path:
    return plan_state_dir(state_root, plan_name) / "checkpoint.json"


def summary_path(state_root: Path, plan_name: str) -> Path:
    return plan_state_dir(state_root, plan_name) / "summary.json"


def history_path(state_root: Path) -> Path:
    return state_root / "duration_history.jsonl"


def stage_log_path(state_root: Path, plan_name: str, stage: TestStageSpec) -> Path:
    return plan_state_dir(state_root, plan_name) / "logs" / f"{stage.stage_id}.log"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def new_checkpoint(plan: TestPlanSpec) -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "plan_name": plan.name,
        "plan_fingerprint": plan.fingerprint,
        "workspace_fingerprint": plan.workspace_fingerprint,
        "started_at": now,
        "updated_at": now,
        "stages": {},
    }


def load_checkpoint(state_root: Path, plan_name: str) -> dict[str, Any] | None:
    path = checkpoint_path(state_root, plan_name)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def save_checkpoint(state_root: Path, checkpoint: dict[str, Any]) -> None:
    checkpoint["updated_at"] = utc_now()
    _atomic_write_json(checkpoint_path(state_root, str(checkpoint["plan_name"])), checkpoint)


def validate_checkpoint(plan: TestPlanSpec, checkpoint: dict[str, Any]) -> tuple[bool, str]:
    if checkpoint.get("schema_version") != STATE_SCHEMA_VERSION:
        return False, "checkpoint schema changed"
    if checkpoint.get("plan_name") != plan.name:
        return False, "checkpoint belongs to another plan"
    if checkpoint.get("plan_fingerprint") != plan.fingerprint:
        return False, "test manifest changed"
    return True, ""


def completed_stage_ids(checkpoint: dict[str, Any]) -> set[str]:
    records = checkpoint.get("stages", {})
    if not isinstance(records, dict):
        return set()
    return {
        stage_id
        for stage_id, record in records.items()
        if isinstance(record, dict) and record.get("status") == "PASS"
    }


def mark_stage_running(
    state_root: Path,
    checkpoint: dict[str, Any],
    stage: TestStageSpec,
    *,
    log_path: Path,
) -> str:
    started_at = utc_now()
    stages = checkpoint.setdefault("stages", {})
    stages[stage.stage_id] = {
        "stage_id": stage.stage_id,
        "label": stage.label,
        "group_id": stage.group_id,
        "timeout_seconds": stage.timeout_seconds,
        "fingerprint": stage.fingerprint,
        "status": "RUNNING",
        "return_code": None,
        "elapsed_seconds": None,
        "log_path": str(log_path),
        "started_at": started_at,
        "finished_at": "",
    }
    save_checkpoint(state_root, checkpoint)
    return started_at


def record_stage_result(
    state_root: Path,
    checkpoint: dict[str, Any],
    stage: TestStageSpec,
    result: StageRunResult,
) -> None:
    stages = checkpoint.setdefault("stages", {})
    record = result.to_record(fingerprint=stage.fingerprint)
    record["group_id"] = stage.group_id
    record["timeout_seconds"] = stage.timeout_seconds
    stages[stage.stage_id] = record
    save_checkpoint(state_root, checkpoint)
    append_duration_history(state_root, checkpoint["plan_name"], stage, result)


def append_duration_history(
    state_root: Path,
    plan_name: str,
    stage: TestStageSpec,
    result: StageRunResult,
) -> None:
    path = history_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "recorded_at": utc_now(),
        "plan_name": plan_name,
        "stage_id": stage.stage_id,
        "stage_fingerprint": stage.fingerprint,
        "label": stage.label,
        "group_id": stage.group_id,
        "timeout_seconds": stage.timeout_seconds,
        "status": result.status,
        "elapsed_seconds": round(result.elapsed_seconds, 3),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def prior_duration_median(
    state_root: Path,
    stage: TestStageSpec,
    *,
    sample_limit: int = 20,
) -> float | None:
    path = history_path(state_root)
    if not path.exists():
        return None
    durations: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            record.get("stage_id") == stage.stage_id
            and record.get("stage_fingerprint") == stage.fingerprint
            and record.get("status") == "PASS"
        ):
            try:
                durations.append(float(record["elapsed_seconds"]))
            except (KeyError, TypeError, ValueError):
                continue
    if not durations:
        return None
    return float(median(durations[-sample_limit:]))


def build_summary(
    plan: TestPlanSpec,
    checkpoint: dict[str, Any],
    selected_stage_ids: Iterable[str],
) -> dict[str, Any]:
    selected = set(selected_stage_ids)
    records = checkpoint.get("stages", {}) if isinstance(checkpoint.get("stages"), dict) else {}
    stage_rows: list[dict[str, Any]] = []
    counts = {"PASS": 0, "FAIL": 0, "TIMEOUT": 0, "NOT_RUN": 0, "RUNNING": 0}
    total_seconds = 0.0
    group_rows: dict[str, dict[str, Any]] = {}

    for index, stage in enumerate(plan.stages, start=1):
        record = records.get(stage.stage_id, {}) if isinstance(records, dict) else {}
        status = str(record.get("status", "NOT_RUN"))
        if stage.stage_id not in selected and status not in {"PASS", "FAIL", "TIMEOUT"}:
            status = "NOT_RUN"
        if status not in counts:
            status = "NOT_RUN"
        counts[status] += 1

        elapsed_value = record.get("elapsed_seconds")
        elapsed = float(elapsed_value) if isinstance(elapsed_value, (int, float)) else None
        if elapsed is not None:
            total_seconds += elapsed
        boundary_exceeded = bool(
            elapsed is not None and elapsed > TEST_STAGE_BOUNDARY_SECONDS
        )
        group_id = stage.group_id or plan.name
        stage_rows.append(
            {
                "number": index,
                "stage_id": stage.stage_id,
                "group_id": group_id,
                "label": stage.label,
                "status": status,
                "elapsed_seconds": elapsed_value,
                "timeout_seconds": stage.timeout_seconds,
                "boundary_exceeded": boundary_exceeded,
                "log_path": record.get("log_path", ""),
            }
        )

        group = group_rows.setdefault(
            group_id,
            {
                "group_id": group_id,
                "elapsed_seconds": 0.0,
                "stage_count": 0,
                "passed": 0,
                "failed": 0,
                "timed_out": 0,
                "not_run": 0,
                "boundary_exceeded_stages": 0,
            },
        )
        group["stage_count"] += 1
        if elapsed is not None:
            group["elapsed_seconds"] += elapsed
        if status == "PASS":
            group["passed"] += 1
        elif status == "FAIL":
            group["failed"] += 1
        elif status == "TIMEOUT":
            group["timed_out"] += 1
        else:
            group["not_run"] += 1
        if boundary_exceeded:
            group["boundary_exceeded_stages"] += 1

    groups = list(group_rows.values())
    for group in groups:
        group["elapsed_seconds"] = round(float(group["elapsed_seconds"]), 3)

    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "plan_name": plan.name,
        "plan_fingerprint": plan.fingerprint,
        "workspace_fingerprint": plan.workspace_fingerprint,
        "generated_at": utc_now(),
        "stage_boundary_seconds": TEST_STAGE_BOUNDARY_SECONDS,
        "counts": counts,
        "total_recorded_stage_seconds": round(total_seconds, 3),
        "groups": groups,
        "stages": stage_rows,
    }


def write_summary(state_root: Path, plan: TestPlanSpec, summary: dict[str, Any]) -> Path:
    path = summary_path(state_root, plan.name)
    _atomic_write_json(path, summary)
    return path
