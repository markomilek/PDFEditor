"""Command-line interface for PDFEditor."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Sequence

from pdfeditor.models import RunConfig
from pdfeditor.processor import process_pdf
from pdfeditor.reporting import build_run_result, write_run_reports

EDITED_INPUT_PATTERN = re.compile(r"\.edited(?:\.\d+)?\.pdf\Z", re.IGNORECASE)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(prog="pdfeditor")
    parser.add_argument("--path", default=".", help="Directory to scan for PDF files.")
    parser.add_argument(
        "--out",
        default=None,
        help="Directory for edited PDF outputs. Defaults to --path.",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Directory for JSON and text reports. Defaults to --path.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subdirectories recursively for PDF files.",
    )
    parser.add_argument(
        "--write-when-unchanged",
        action="store_true",
        help="Write a copy even when no pages are removed.",
    )
    parser.add_argument(
        "--treat-annotations-as-empty",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Treat annotation-only pages as empty. Enabled by default.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report planned changes without writing edited PDFs.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-file processing details.",
    )
    return parser


def run_cli(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = build_parser().parse_args(argv)

    scan_path = Path(args.path)
    out_dir = Path(args.out) if args.out is not None else scan_path
    report_dir = Path(args.report_dir) if args.report_dir is not None else scan_path

    config = RunConfig(
        path=str(scan_path),
        out=str(out_dir),
        report_dir=str(report_dir),
        recursive=bool(args.recursive),
        write_when_unchanged=bool(args.write_when_unchanged),
        treat_annotations_as_empty=bool(args.treat_annotations_as_empty),
        dry_run=bool(args.dry_run),
        verbose=bool(args.verbose),
    )

    files = []
    run_warnings: list[str] = []
    run_errors: list[str] = []

    report_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not scan_path.exists() or not scan_path.is_dir():
        run_errors.append(f"Scan path is not a directory: {scan_path}")
    else:
        for pdf_path in discover_pdfs(scan_path, recursive=config.recursive):
            file_result = process_pdf(pdf_path, out_dir=out_dir, config=config)
            files.append(file_result)
            if config.verbose:
                print(
                    f"{file_result.status}: {pdf_path} "
                    f"(removed={file_result.pages_removed}, output={file_result.output_path or '-'})"
                )

    run_result = build_run_result(
        config=config,
        files=files,
        warnings=run_warnings,
        errors=run_errors,
    )
    json_path, txt_path = write_run_reports(run_result=run_result, report_dir=report_dir)

    print(f"pdfeditor: processed {len(files)} file(s)")
    print(f"pdfeditor: reports written to {json_path} and {txt_path}")

    has_failures = run_result.totals["files_failed"] > 0 or bool(run_result.errors)
    return 2 if has_failures else 0


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI as a console entry point."""
    raise SystemExit(run_cli(argv))


def discover_pdfs(path: Path, recursive: bool) -> list[Path]:
    """Discover candidate PDFs for processing."""
    if recursive:
        iterator = sorted(item for item in path.rglob("*") if item.is_file())
    else:
        iterator = sorted(item for item in path.iterdir() if item.is_file())

    candidates: list[Path] = []
    for item in iterator:
        if item.suffix.lower() != ".pdf":
            continue
        if EDITED_INPUT_PATTERN.search(item.name):
            continue
        candidates.append(item)
    return candidates
