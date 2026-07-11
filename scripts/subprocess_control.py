"""Run subprocesses with reliable timeout and descendant cleanup."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ControlledProcessResult:
    return_code: int
    timed_out: bool = False


def _popen_group_kwargs() -> dict[str, object]:
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return {"start_new_session": True}


def _terminate_process_tree(process: subprocess.Popen[object]) -> None:
    """Terminate a process and descendants without leaving a hung test worker."""

    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait(timeout=5)


def run_controlled_process(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> ControlledProcessResult:
    """Run a command and return 124 after killing its whole process tree."""

    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdin=subprocess.DEVNULL,
        **_popen_group_kwargs(),
    )
    try:
        return ControlledProcessResult(process.wait(timeout=timeout_seconds))
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        return ControlledProcessResult(124, timed_out=True)
