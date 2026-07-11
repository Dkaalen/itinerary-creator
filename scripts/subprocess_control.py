"""Run subprocesses with reliable timeout, streaming logs, and tree cleanup."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from typing import Mapping, Sequence, TextIO


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


def _reader_loop(
    stream: TextIO,
    log_handle: TextIO,
    last_output: list[float],
) -> None:
    try:
        for line in iter(stream.readline, ""):
            if not line:
                break
            sys.stdout.write(line)
            sys.stdout.flush()
            log_handle.write(line)
            log_handle.flush()
            last_output[0] = time.monotonic()
    finally:
        stream.close()


def _install_termination_handlers(process: subprocess.Popen[object]) -> dict[int, object]:
    """Ensure a killed orchestrator does not orphan its current test stage."""

    if threading.current_thread() is not threading.main_thread():
        return {}
    previous: dict[int, object] = {}

    def _handler(signum: int, _frame: object) -> None:
        _terminate_process_tree(process)
        raise SystemExit(128 + signum)

    for signum in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if signum is None:
            continue
        previous[signum] = signal.getsignal(signum)
        signal.signal(signum, _handler)
    return previous


def _restore_handlers(previous: dict[int, object]) -> None:
    if threading.current_thread() is not threading.main_thread():
        return
    for signum, handler in previous.items():
        signal.signal(signum, handler)


def _run_streaming_process(
    process: subprocess.Popen[str],
    *,
    timeout_seconds: float | None,
    log_path: Path,
    heartbeat_seconds: float,
    heartbeat_label: str,
) -> ControlledProcessResult:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    last_output = [started]
    last_heartbeat = started
    previous_handlers = _install_termination_handlers(process)
    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            assert process.stdout is not None
            reader = threading.Thread(
                target=_reader_loop,
                args=(process.stdout, log_handle, last_output),
                name="test-stage-output",
                daemon=True,
            )
            reader.start()
            timed_out = False
            while process.poll() is None:
                now = time.monotonic()
                if timeout_seconds is not None and now - started >= timeout_seconds:
                    timed_out = True
                    timeout_line = (
                        f"\n[timeout] {heartbeat_label} exceeded {timeout_seconds:.0f}s; "
                        "terminating the full process tree.\n"
                    )
                    sys.stdout.write(timeout_line)
                    sys.stdout.flush()
                    log_handle.write(timeout_line)
                    log_handle.flush()
                    _terminate_process_tree(process)
                    break
                if (
                    heartbeat_seconds > 0
                    and now - last_output[0] >= heartbeat_seconds
                    and now - last_heartbeat >= heartbeat_seconds
                ):
                    elapsed = now - started
                    heartbeat = f"[heartbeat] {heartbeat_label} still running at {elapsed:.1f}s\n"
                    sys.stdout.write(heartbeat)
                    sys.stdout.flush()
                    log_handle.write(heartbeat)
                    log_handle.flush()
                    last_heartbeat = now
                time.sleep(0.2)
            reader.join(timeout=5)
            if timed_out:
                return ControlledProcessResult(124, timed_out=True)
            return ControlledProcessResult(int(process.returncode or 0))
    finally:
        _restore_handlers(previous_handlers)


def run_controlled_process(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float | None = None,
    log_path: str | Path | None = None,
    heartbeat_seconds: float = 0,
    heartbeat_label: str = "process",
) -> ControlledProcessResult:
    """Run a command and return 124 after killing its whole process tree.

    When ``log_path`` is provided, stdout and stderr are continuously tee'd to
    both the console and the stage log. Heartbeats keep long silent stages
    observable without changing their timeout semantics.
    """

    streaming = log_path is not None
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if streaming else None,
        stderr=subprocess.STDOUT if streaming else None,
        text=streaming,
        bufsize=1 if streaming else -1,
        **_popen_group_kwargs(),
    )
    if streaming:
        return _run_streaming_process(
            process,
            timeout_seconds=timeout_seconds,
            log_path=Path(log_path),
            heartbeat_seconds=heartbeat_seconds,
            heartbeat_label=heartbeat_label,
        )

    previous_handlers = _install_termination_handlers(process)
    try:
        return ControlledProcessResult(process.wait(timeout=timeout_seconds))
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        return ControlledProcessResult(124, timed_out=True)
    finally:
        _restore_handlers(previous_handlers)
