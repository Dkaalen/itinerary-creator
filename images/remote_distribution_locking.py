"""File lock helpers for remote image-bank distribution."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
import os
import time

from images.remote_distribution_config import lock_timeout_seconds
from images.remote_distribution_models import DistributionError


@contextmanager
def file_lock(lock_path: Path, *, timeout_seconds: Callable[[], float] = lock_timeout_seconds):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds()
    stale_after = max(timeout_seconds() * 2.0, 300.0)
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, f"{os.getpid()}\n{time.time()}\n".encode("ascii"))
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > stale_after:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise DistributionError("Timed out waiting for another image-bank download to finish.")
            time.sleep(0.2)
    try:
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        lock_path.unlink(missing_ok=True)
