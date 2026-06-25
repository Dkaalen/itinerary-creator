"""Normalize image-bank roots and read cheap filesystem signatures."""

from pathlib import Path
import diagnostics


def coerce_image_bank_paths(image_bank_path: Path | str | list | tuple | set = "image_bank") -> list[Path]:
    values = list(image_bank_path) if isinstance(image_bank_path, (list, tuple, set)) else [image_bank_path]
    paths, seen = [], set()
    for value in values:
        if not value: continue
        path = Path(value).expanduser(); key = resolved_path_text(path)
        if key not in seen: seen.add(key); paths.append(path)
    return paths


def resolved_path_text(path: Path) -> str:
    try: return str(path.resolve())
    except OSError: return str(path)


def stat_signature(path: Path) -> tuple[int, int] | None:
    try: stat = path.stat()
    except OSError as error:
        diagnostics.warn_exception("image_bank_scan", "Could not read image-bank file metadata.", error, str(path), source="images.scanner")
        return None
    return int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))), int(stat.st_size)


def path_set_key(image_bank_path: Path | str | list | tuple | set = "image_bank") -> tuple[str, ...]:
    return tuple(resolved_path_text(path) for path in coerce_image_bank_paths(image_bank_path))


def fast_paths_signature(path_key: tuple[str, ...]) -> tuple[tuple[str, int, int], ...]:
    signature = []
    for text in path_key:
        path = Path(text)
        signature.append((text, *((stat_signature(path) if path.exists() else None) or (0, 0))))
    return tuple(signature)
