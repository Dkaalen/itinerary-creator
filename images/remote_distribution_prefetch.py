"""Opportunistic remote image-bank prefetching."""

from __future__ import annotations

from pathlib import Path
from threading import Lock, Thread
from typing import Any

from images.remote_distribution_config import normalise_lookup
from images.remote_manifest import ensure_destination_packs
from images.remote_pack_resolver import destination_requests_from_rows

PREFETCH_LOCK = Lock()
PREFETCH_IN_FLIGHT: set[str] = set()


def schedule_destination_prefetch(app_root: Path, rows_or_grouped_days: Any) -> bool:
    """Start a daemon prefetch once per destination set without blocking generation."""

    requests = destination_requests_from_rows(rows_or_grouped_days)
    if not requests:
        return False
    try:
        root_key = str(app_root.resolve())
    except OSError:
        root_key = str(app_root)
    signature = root_key + "|" + "|".join(
        sorted(f"{normalise_lookup(item.country)}/{normalise_lookup(item.destination)}" for item in requests)
    )
    with PREFETCH_LOCK:
        if signature in PREFETCH_IN_FLIGHT:
            return False
        PREFETCH_IN_FLIGHT.add(signature)

    def run() -> None:
        try:
            ensure_destination_packs(app_root, requests)
        except Exception:
            pass
        finally:
            with PREFETCH_LOCK:
                PREFETCH_IN_FLIGHT.discard(signature)

    Thread(target=run, name="image-bank-prefetch", daemon=True).start()
    return True
