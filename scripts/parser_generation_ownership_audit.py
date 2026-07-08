"""Audit parser/generation ownership drift without changing behavior.

The report is intentionally informational. It highlights places where later
layers may be re-interpreting parser truth so cleanup can be evidence-led.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_JSON = REPO_ROOT / "docs/reports/parser_generation_ownership/latest.json"
DEFAULT_MD = REPO_ROOT / "docs/reports/parser_generation_ownership/latest.md"

IGNORED_DIRS = {".git", ".pytest_cache", "__pycache__", "venv", ".venv", "node_modules"}
OWNERSHIP_TARGETS = (
    "parser row type",
    "effective type",
    "normalized event",
    "DayFacts",
    "DayIntent",
    "DayCopyPlan",
    "DayRenderModel",
    "PDF/render context",
)


@dataclass(frozen=True)
class OwnershipSignal:
    rule_id: str
    severity: str
    path: str
    line: int
    message: str
    snippet: str


@dataclass(frozen=True)
class OwnershipReport:
    scanned_files: int
    signal_count: int
    signals_by_rule: dict[str, int]
    signals: tuple[OwnershipSignal, ...]
    ownership_targets: tuple[str, ...] = OWNERSHIP_TARGETS

    def to_dict(self) -> dict:
        return {
            "scanned_files": self.scanned_files,
            "signal_count": self.signal_count,
            "signals_by_rule": self.signals_by_rule,
            "ownership_targets": list(self.ownership_targets),
            "signals": [asdict(signal) for signal in self.signals],
        }


def _iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        parts = set(path.relative_to(root).parts)
        if parts & IGNORED_DIRS:
            continue
        if path.relative_to(root).parts[0] == "tests":
            continue
        yield path


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _allowed(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)


def _line_has_type_branch(line: str) -> bool:
    return bool(re.search(r"\b(?:effective_type|source_type|row_type|type)\b", line)) and bool(re.search(r"\b(?:if|elif|case| in | == |!=)\b", line))


def _scan_file(root: Path, path: Path) -> list[OwnershipSignal]:
    rel = _rel(root, path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    signals: list[OwnershipSignal] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lowered = stripped.casefold()
        if _route_extraction_drift(rel, stripped, lowered):
            signals.append(
                OwnershipSignal(
                    rule_id="route_extraction_outside_parser_or_transport_domain",
                    severity="review",
                    path=rel,
                    line=lineno,
                    message="Route extraction signal outside parser/transport-domain ownership.",
                    snippet=stripped[:220],
                )
            )
        if _city_detection_in_render(rel, stripped, lowered):
            signals.append(
                OwnershipSignal(
                    rule_id="city_detection_inside_render_layer",
                    severity="review",
                    path=rel,
                    line=lineno,
                    message="Render/PDF layer appears to inspect destination/city truth directly.",
                    snippet=stripped[:220],
                )
            )
        if _classification_in_writer(rel, stripped):
            signals.append(
                OwnershipSignal(
                    rule_id="classification_inside_writer_layer",
                    severity="review",
                    path=rel,
                    line=lineno,
                    message="Writer/render layer branches on row classification instead of using prepared plans/facts.",
                    snippet=stripped[:220],
                )
            )
        if _pdf_product_truth_override(rel, stripped, lowered):
            signals.append(
                OwnershipSignal(
                    rule_id="pdf_layer_product_truth_override",
                    severity="watch",
                    path=rel,
                    line=lineno,
                    message="PDF layer contains text/product normalization signal; verify it only formats render models.",
                    snippet=stripped[:220],
                )
            )
        if _parser_imports_generation(rel, stripped):
            signals.append(
                OwnershipSignal(
                    rule_id="parser_imports_generation_layer",
                    severity="risk",
                    path=rel,
                    line=lineno,
                    message="Parser layer imports generation layer; parser should produce truth without copy/render dependencies.",
                    snippet=stripped[:220],
                )
            )
    return signals


def _route_extraction_drift(path: str, line: str, lowered: str) -> bool:
    if _allowed(
        path,
        (
            "parser_modules",
            "normalizer_modules",
            "itinerary_parser.py",
            "normalizer.py",
            "itinerary_generation/transport_domain",
            "itinerary_generation/nutshell_route_parser.py",
            "itinerary_generation/nutshell_route_parsing.py",
            "scripts/parser_generation_ownership_audit.py",
        ),
    ):
        return False
    route_terms = ("extract_route", "route_points", "get_route_points", "_title_route_points")
    return any(term in lowered for term in route_terms)


def _city_detection_in_render(path: str, line: str, lowered: str) -> bool:
    render_path = "day_render" in path or path.startswith("pdf_exporter_modules/") or path.startswith("app_modules/preview")
    if not render_path:
        return False
    city_terms = ("destination_registry", "known_city", "known_cities", "extract_city", "city_re", "detect_city", "find_destination")
    return any(term in lowered for term in city_terms)


def _classification_in_writer(path: str, line: str) -> bool:
    writer_path = any(marker in path for marker in ("day_intro", "day_render", "summaries", "copy", "pdf_exporter_modules"))
    if not writer_path:
        return False
    return _line_has_type_branch(line)


def _pdf_product_truth_override(path: str, line: str, lowered: str) -> bool:
    if not path.startswith("pdf_exporter_modules/"):
        return False
    if "pdf_exporter_modules/pdf_internal_review_appendix.py" == path:
        return False
    return any(term in lowered for term in ("effective_type", "source_type", "fix_common_text", "clean_title", "normalize_itinerary", "re.sub", ".replace("))


def _parser_imports_generation(path: str, line: str) -> bool:
    if not _allowed(path, ("parser_modules", "normalizer_modules", "itinerary_parser.py", "normalizer.py")):
        return False
    if re.match(r"\s*(?:from|import)\s+itinerary_generation\.transport_domain\b", line):
        return False
    return bool(re.match(r"\s*(?:from|import)\s+itinerary_generation\b", line))


def build_report(root: Path = REPO_ROOT) -> OwnershipReport:
    files = list(_iter_python_files(root))
    signals: list[OwnershipSignal] = []
    for path in files:
        signals.extend(_scan_file(root, path))
    signals_by_rule: dict[str, int] = {}
    for signal in signals:
        signals_by_rule[signal.rule_id] = signals_by_rule.get(signal.rule_id, 0) + 1
    return OwnershipReport(
        scanned_files=len(files),
        signal_count=len(signals),
        signals_by_rule=dict(sorted(signals_by_rule.items())),
        signals=tuple(signals),
    )


def markdown_report(report: OwnershipReport) -> str:
    lines = [
        "# Parser/Generation Ownership Audit",
        "",
        "Generated by `scripts/parser_generation_ownership_audit.py`.",
        "",
        f"Scanned files: `{report.scanned_files}`",
        f"Signals: `{report.signal_count}`",
        "",
        "## Ownership targets",
    ]
    lines.extend(f"- {target}" for target in report.ownership_targets)
    lines.extend(["", "## Signals by rule"])
    if report.signals_by_rule:
        for rule_id, count in report.signals_by_rule.items():
            lines.append(f"- `{rule_id}`: {count}")
    else:
        lines.append("- None detected")
    lines.extend(["", "## Highest-priority review items"])
    priority = sorted(report.signals, key=lambda item: ({"risk": 0, "review": 1, "watch": 2}.get(item.severity, 3), item.path, item.line))[:80]
    if priority:
        for signal in priority:
            lines.append(f"- `{signal.severity}` `{signal.rule_id}` · `{signal.path}:{signal.line}` — {signal.snippet}")
    else:
        lines.append("- None detected")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is an audit, not a guard. Signals need human review before refactor or deletion.",
            "Parser/normalizer should own row and route truth; generation should consume prepared facts/plans; PDF should only render the prepared document model.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_report(report: OwnershipReport, *, json_path: Path = DEFAULT_JSON, md_path: Path = DEFAULT_MD) -> tuple[Path, Path]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit parser/generation ownership drift.")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    parser.add_argument("--md-output", default=str(DEFAULT_MD))
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(Path(args.root))
    if args.no_write:
        print(markdown_report(report), end="")
    else:
        json_path, md_path = write_report(report, json_path=Path(args.json_output), md_path=Path(args.md_output))
        print(f"Wrote {json_path}")
        print(f"Wrote {md_path}")
        print(f"signals={report.signal_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
