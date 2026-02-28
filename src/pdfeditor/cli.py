"""Command-line interface for PDFEditor."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Sequence

from pdfeditor.detect_render import is_render_backend_available
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
        "--mode",
        choices=("structural", "render", "both"),
        default="both",
        help="Empty-page detection mode. Defaults to both.",
    )
    parser.add_argument(
        "--render-dpi",
        type=int,
        default=72,
        help="DPI used for rendering-based detection.",
    )
    parser.add_argument(
        "--ink-threshold",
        type=float,
        default=0.0005,
        help="Fraction of non-background pixels required to treat a page as non-empty.",
    )
    parser.add_argument(
        "--background",
        choices=("white", "auto"),
        default="white",
        help="Background assumption for render detection. 'auto' currently falls back to white.",
    )
    parser.add_argument(
        "--render-sample",
        choices=("all", "center"),
        default="all",
        help="Region of the rendered page used for ink sampling.",
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
        "--debug-structural",
        action="store_true",
        help="Write per-page structural detector debug JSON files to --report-dir.",
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

    run_warnings: list[str] = []
    run_errors: list[str] = []
    effective_mode = args.mode
    if args.background == "auto":
        run_warnings.append("Background mode 'auto' is not implemented yet; using white.")
    effective_background = "white"

    render_available = is_render_backend_available()
    if args.mode == "render" and not render_available:
        run_errors.append("Render mode requires optional dependency 'pypdfium2'.")
    elif args.mode == "both" and not render_available:
        run_warnings.append(
            "Render mode requested via --mode both, but pypdfium2 is unavailable; "
            "falling back to structural-only detection."
        )
        effective_mode = "structural"

    config = RunConfig(
        path=str(scan_path),
        out=str(out_dir),
        report_dir=str(report_dir),
        mode=str(args.mode),
        effective_mode=effective_mode,
        render_dpi=int(args.render_dpi),
        ink_threshold=float(args.ink_threshold),
        background=str(args.background),
        effective_background=effective_background,
        render_sample=str(args.render_sample),
        recursive=bool(args.recursive),
        write_when_unchanged=bool(args.write_when_unchanged),
        treat_annotations_as_empty=bool(args.treat_annotations_as_empty),
        dry_run=bool(args.dry_run),
        debug_structural=bool(args.debug_structural),
        verbose=bool(args.verbose),
    )

    files = []

    report_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    if run_errors:
        pass
    elif not scan_path.exists() or not scan_path.is_dir():
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
                if file_result.structural_debug_path is not None:
                    print(f"wrote structural debug to {file_result.structural_debug_path}")

    run_result = build_run_result(
        config=config,
        files=files,
        warnings=run_warnings,
        errors=run_errors,
    )
    json_path, txt_path = write_run_reports(run_result=run_result, report_dir=report_dir)

    for error in run_errors:
        print(f"pdfeditor: error: {error}")
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
