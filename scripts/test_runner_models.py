"""Small data models for the staged test orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class TestStageSpec:
    """One independently executable validation stage."""

    stage_id: str
    label: str
    command: tuple[str, ...]
    timeout_seconds: int
    kind: str = "pytest"
    targets: tuple[str, ...] = ()

    @property
    def fingerprint(self) -> str:
        payload = {
            "stage_id": self.stage_id,
            "label": self.label,
            "command": list(self.command),
            "timeout_seconds": self.timeout_seconds,
            "kind": self.kind,
            "targets": list(self.targets),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class TestPlanSpec:
    """Stable ordered stage manifest for one validation plan."""

    name: str
    description: str
    stages: tuple[TestStageSpec, ...]
    workspace_fingerprint: str = ""

    @property
    def fingerprint(self) -> str:
        payload = {
            "name": self.name,
            "description": self.description,
            "stages": [stage.fingerprint for stage in self.stages],
            "workspace_fingerprint": self.workspace_fingerprint,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class StageRunResult:
    """One stage result with enough metadata for honest resume reporting."""

    label: str
    return_code: int
    elapsed_seconds: float
    stage_id: str = ""
    log_path: str = ""
    started_at: str = ""
    finished_at: str = ""
    prior_median_seconds: float | None = None

    @property
    def passed(self) -> bool:
        return self.return_code == 0

    @property
    def timed_out(self) -> bool:
        return self.return_code == 124

    @property
    def status(self) -> str:
        if self.timed_out:
            return "TIMEOUT"
        if self.passed:
            return "PASS"
        return "FAIL"

    def to_record(self, *, fingerprint: str) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "label": self.label,
            "fingerprint": fingerprint,
            "status": self.status,
            "return_code": self.return_code,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "log_path": self.log_path,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "prior_median_seconds": self.prior_median_seconds,
        }

# Prevent pytest from mistaking imported data models for test classes.
TestStageSpec.__test__ = False
TestPlanSpec.__test__ = False
