"""Recursive image-bank fingerprinting and metadata extraction."""

from functools import lru_cache
import hashlib
from pathlib import Path
import diagnostics

from images.image_bank_paths import coerce_image_bank_paths, resolved_path_text, stat_signature
from images.metadata import IMAGE_EXTENSIONS, ImageCandidate, extract_image_metadata


def scan_cache_key(image_bank_path: Path | str | list | tuple | set = "image_bank") -> tuple[tuple[str, int, int, int, str], ...]:
    key = []
    for base in coerce_image_bank_paths(image_bank_path):
        resolved = Path(resolved_path_text(base))
        if not base.exists(): key.append((str(resolved), 0, 0, 0, "")); continue
        newest, count, size, fingerprint = (stat_signature(base) or (0, 0))[0], 0, 0, hashlib.sha1()
        try: paths = sorted(base.rglob("*"))
        except OSError as error:
            diagnostics.warn_exception("image_bank_scan", "Could not walk image-bank folder.", error, str(base), source="images.scanner"); key.append((str(resolved), newest, 0, 0, "walk-error")); continue
        for path in paths:
            try:
                if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS: continue
            except OSError as error:
                diagnostics.warn_exception("image_bank_scan", "Could not inspect image-bank path.", error, str(path), source="images.scanner"); continue
            signature = stat_signature(path)
            if signature is None: continue
            mtime, file_size = signature; count += 1; size += file_size; newest = max(newest, mtime)
            try: relative = path.relative_to(base)
            except ValueError: relative = path
            fingerprint.update(str(relative).replace("\\", "/").encode("utf-8", "surrogateescape")); fingerprint.update(f":{mtime}:{file_size};".encode("ascii"))
        key.append((str(resolved), newest, count, size, fingerprint.hexdigest()))
    return tuple(key)


@lru_cache(maxsize=16)
def scan_image_bank_cached(cache_key: tuple[tuple[str, int, int, int, str], ...]) -> tuple[ImageCandidate, ...]:
    candidates, seen = [], set()
    for path_text, *_ in cache_key:
        base = Path(path_text)
        if not base.exists() or not base.is_dir(): continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS: continue
            try: key = str(path.resolve())
            except OSError as error:
                diagnostics.warn_exception("image_bank_scan", "Could not resolve image-bank file path.", error, str(path), source="images.scanner"); continue
            if key in seen: continue
            seen.add(key)
            try: candidates.append(extract_image_metadata(path, base))
            except (OSError, ValueError, UnicodeError) as error: diagnostics.warn_exception("image_bank_scan", "Could not read image-bank metadata.", error, str(path), source="images.scanner")
    return tuple(candidates)
