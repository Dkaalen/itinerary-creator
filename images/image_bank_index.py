"""Reusable image-bank index model and index construction."""

from dataclasses import dataclass
from pathlib import Path

from images.image_bank_paths import resolved_path_text
from images.image_bank_scan import scan_image_bank_cached
from images.metadata import ImageCandidate, city_variants, normalize_keyword


@dataclass(slots=True)
class ImageBankIndex:
    paths: tuple[str, ...]
    cache_key: tuple[tuple[str, int, int, int, str], ...]
    candidates: tuple[ImageCandidate, ...]
    by_path: dict[str, ImageCandidate]
    by_city_variant: dict[str, tuple[ImageCandidate, ...]]
    defaults: tuple[ImageCandidate, ...]
    destination_candidates: tuple[ImageCandidate, ...]
    destination_roots: tuple[str, ...]
    countries: tuple[str, ...]
    destinations: tuple[str, ...]
    by_root: dict[str, tuple[ImageCandidate, ...]]
    order_by_path: dict[str, int]

    def candidates_for_city(self, city: str, *, include_defaults: bool = True) -> tuple[ImageCandidate, ...]:
        return self._candidate_union(city_variants(city), include_defaults=include_defaults)

    def candidates_for_context(self, context: dict, *, include_defaults: bool = True) -> tuple[ImageCandidate, ...]:
        keys = {
            normalize_keyword(value)
            for value in context.get("city_variants", set())
            if normalize_keyword(value)
        }
        return self._candidate_union(keys, include_defaults=include_defaults)

    def root_candidates(self, root: Path | str) -> tuple[ImageCandidate, ...]:
        return self.by_root.get(resolved_path_text(Path(root)), ())

    def _candidate_union(self, keys: set[str], *, include_defaults: bool) -> tuple[ImageCandidate, ...]:
        selected = {}
        for key in keys:
            for candidate in self.by_city_variant.get(key, ()):
                selected.setdefault(resolved_path_text(Path(candidate.path)), candidate)
        if include_defaults:
            for candidate in self.defaults:
                selected.setdefault(resolved_path_text(Path(candidate.path)), candidate)
        return tuple(
            sorted(
                selected.values(),
                key=lambda candidate: self.order_by_path.get(resolved_path_text(Path(candidate.path)), 0),
            )
        )


def _candidate_root(candidate: ImageCandidate, roots: tuple[str, ...]) -> str:
    path = Path(candidate.path)
    try:
        path = path.resolve()
    except OSError:
        pass
    for root_text in roots:
        try:
            if path.is_relative_to(Path(root_text).resolve()):
                return root_text
        except (OSError, ValueError):
            continue
    return ""


def build_image_bank_index(
    paths: tuple[str, ...],
    cache_key: tuple[tuple[str, int, int, int, str], ...],
) -> ImageBankIndex:
    candidates = scan_image_bank_cached(cache_key)
    by_path: dict[str, ImageCandidate] = {}
    cities: dict[str, list[ImageCandidate]] = {}
    defaults: list[ImageCandidate] = []
    destinations: list[ImageCandidate] = []
    roots: dict[str, list[ImageCandidate]] = {path: [] for path in paths}
    order: dict[str, int] = {}

    for index, candidate in enumerate(candidates):
        key = resolved_path_text(Path(candidate.path))
        by_path[key] = candidate
        order[key] = index
        target = defaults if normalize_keyword(candidate.city) in {"default", "defoult"} else destinations
        target.append(candidate)
        for city_key in city_variants(candidate.city):
            cities.setdefault(city_key, []).append(candidate)
        root = _candidate_root(candidate, paths)
        if root:
            roots.setdefault(root, []).append(candidate)

    destination_roots = tuple(
        root
        for root, values in roots.items()
        if any(normalize_keyword(item.city) not in {"default", "defoult"} for item in values)
    )
    countries = tuple(sorted({str(item.country).strip() for item in destinations if str(item.country).strip()}))
    destination_names = tuple(sorted({str(item.city).strip() for item in destinations if str(item.city).strip()}))

    return ImageBankIndex(
        paths=paths,
        cache_key=cache_key,
        candidates=candidates,
        by_path=by_path,
        by_city_variant={key: tuple(values) for key, values in cities.items()},
        defaults=tuple(defaults),
        destination_candidates=tuple(destinations),
        destination_roots=destination_roots,
        countries=countries,
        destinations=destination_names,
        by_root={key: tuple(values) for key, values in roots.items()},
        order_by_path=order,
    )
