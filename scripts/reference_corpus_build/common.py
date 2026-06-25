"""Shared constants and file helpers for reference-corpus builders."""

import csv
import hashlib
from pathlib import Path
from place_aliases import canonicalize_place_name

CORPUS_VERSION = "ih1-v1"
SCHEMA_VERSION = 1
TARGET_ICELAND_SHEETS = tuple(f"{days}D {kind}" for kind in ("SD", "GTS", "GTW") for days in (5, 6, 7, 8, 10))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def canonical_place(value: str) -> str: return canonicalize_place_name(value) or str(value or "").strip()


def write_tsv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"); writer.writeheader(); writer.writerows(rows)


def read_three_column_source(path: Path) -> list[tuple[str, str, str]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip(): continue
        parts = line.split("\t", 2)
        if len(parts) != 3: raise ValueError(f"{path.name} line {number} does not contain three tab-separated fields")
        rows.append(tuple(part.strip() for part in parts))
    return rows
