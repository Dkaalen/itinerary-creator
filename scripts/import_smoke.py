"""Import production modules to catch stale or broken module references.

The Streamlit UI dependencies are optional in lightweight test environments, so
missing ``streamlit`` is reported as a permitted skip. Any other import failure
is treated as a broken production import.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PRODUCTION_PACKAGES = (
    "app_modules",
    "images",
    "itinerary_generation",
    "normalizer_modules",
    "parser_modules",
    "pdf_exporter_modules",
    "shared",
    "text_polish_modules",
    "ui",
    "visual_editor_component",
)

OPTIONAL_MISSING_MODULES = frozenset({"streamlit"})


@dataclass(frozen=True)
class ImportFailure:
    module: str
    error_type: str
    message: str
    missing_module: str | None = None


def discover_production_modules(packages: Iterable[str] = PRODUCTION_PACKAGES) -> tuple[str, ...]:
    """Return importable production module names, excluding tests and frontend assets."""

    discovered: set[str] = set()
    for package_name in packages:
        package = importlib.import_module(package_name)
        discovered.add(package_name)
        package_path = getattr(package, "__path__", None)
        if package_path is None:
            continue
        for module_info in pkgutil.walk_packages(package_path, f"{package_name}."):
            name = module_info.name
            if ".tests" in name or ".frontend" in name:
                continue
            discovered.add(name)
    return tuple(sorted(discovered))


def run_import_smoke(
    modules: Iterable[str] | None = None,
    *,
    optional_missing_modules: frozenset[str] = OPTIONAL_MISSING_MODULES,
) -> tuple[tuple[str, ...], tuple[ImportFailure, ...]]:
    """Import production modules and return ``(skipped, failures)``.

    A module is skipped only when its import chain fails because an explicitly
    optional dependency is absent. All other exceptions are returned as failures.
    """

    skipped: list[str] = []
    failures: list[ImportFailure] = []
    for module_name in modules or discover_production_modules():
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            missing = exc.name or ""
            if missing in optional_missing_modules:
                skipped.append(module_name)
                continue
            failures.append(
                ImportFailure(
                    module=module_name,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    missing_module=missing or None,
                )
            )
        except Exception as exc:  # pragma: no cover - exercised only on regressions
            failures.append(
                ImportFailure(
                    module=module_name,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )
    return tuple(skipped), tuple(failures)


def main() -> int:
    skipped, failures = run_import_smoke()
    for failure in failures:
        print(f"FAIL {failure.module}: {failure.error_type}: {failure.message}")
    print(f"Imported production modules; optional skips={len(skipped)}, failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
