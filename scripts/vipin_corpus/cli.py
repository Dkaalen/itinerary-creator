"""Command-line entrypoint for Vipin Excel corpus checks."""

from __future__ import annotations

import argparse
import json

from scripts.vipin_corpus.evaluate import evaluate_excel_corpus
from scripts.vipin_corpus.extract import collect_excel_corpus_items
from scripts.vipin_corpus.io import load_items_jsonl, write_bad_outputs_jsonl, write_items_jsonl
from scripts.vipin_corpus.report import write_markdown_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Vipin Excel parser/generator corpus checks.")
    parser.add_argument("workbooks", nargs="*", help="XLSX workbook paths to scan")
    parser.add_argument("--items-jsonl", help="Read a pre-extracted ExcelCorpusItem JSONL fixture instead of scanning XLSX files.")
    parser.add_argument("--export-items-jsonl", help="Write extracted ExcelCorpusItem rows to this JSONL fixture path.")
    parser.add_argument("--report", default="docs/reports/input4_vipin_excel_corpus_report.md")
    parser.add_argument("--bad-jsonl", default="docs/reports/input4_vipin_excel_bad_outputs.jsonl")
    parser.add_argument("--report-label", default=None, help="Heading label for the markdown report, for example VIPIN_FULL.")
    parser.add_argument("--workers", type=int, default=1, help="Parallel parser workers. Use 4-8 for the full Vipin corpus.")
    parser.add_argument("--chunk-size", type=int, default=5, help="Parser rows per isolated chunk. Keep low for strict regression checks; raise for quick smoke runs.")
    parser.add_argument("--progress", action="store_true", help="Print progress to stderr while parsing chunks.")
    args = parser.parse_args(argv)

    if args.items_jsonl:
        if args.workbooks:
            parser.error("Pass either workbook paths or --items-jsonl, not both.")
        items = load_items_jsonl(args.items_jsonl)
    else:
        if not args.workbooks:
            parser.error("Pass one or more workbook paths, or use --items-jsonl.")
        items = collect_excel_corpus_items(args.workbooks)
    if args.export_items_jsonl:
        write_items_jsonl(items, args.export_items_jsonl)

    summary = evaluate_excel_corpus(items, workers=max(1, args.workers), progress=args.progress, chunk_size=max(1, args.chunk_size))
    write_bad_outputs_jsonl(summary["bad_outputs"], args.bad_jsonl)
    write_markdown_report(summary, args.report, bad_jsonl_path=args.bad_jsonl, report_label=args.report_label)
    print(json.dumps({key: value for key, value in summary.items() if key != "bad_outputs"}, indent=2, ensure_ascii=False))
    return 0 if summary["parse_errors"] == 0 and summary["bulk_generation_ok"] else 1
