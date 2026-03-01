"""Command-line interface for PDFEditor."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import re
from typing import Sequence

from pdfeditor.detect_render import is_render_backend_available
from pdfeditor.models import RunConfig
from pdfeditor.processor import process_pdf
from pdfeditor.reporting import build_run_result, write_run_reports

EDITED_INPUT_PATTERN = re.compile(r"\.edited(?:\.\d+)?\.pdf\Z", re.IGNORECASE)
RenderSampleMargin = tuple[float, float, float, float]
PageNumberBox = tuple[float, float, float, float]


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
        default=1e-5,
        help="Fraction of non-background pixels required to treat a page as non-empty.",
    )
    parser.add_argument(
        "--background",
        choices=("white", "auto"),
        default="white",
        help="Background assumption for render detection. 'auto' currently falls back to white.",
    )
    parser.add_argument(
        "--render-sample-margin",
        type=_parse_render_sample_margin,
        default=(0.0, 0.0, 0.0, 0.0),
        help=(
            "Body sampling margins in inches: TOP,LEFT,RIGHT,BOTTOM. "
            "Sampling excludes these margins from each edge. "
            "Use 0,0,0,0 to sample entire page."
        ),
    )
    parser.add_argument(
        "--white-threshold",
        type=int,
        default=240,
        help="Treat pixels with R,G,B values at or above this threshold as white.",
    )
    parser.add_argument(
        "--stamp-page-numbers",
        action="store_true",
        help="Cover the configured page-number box and stamp corrected page numbers after deletions.",
    )
    parser.add_argument(
        "--stamp-page-numbers-force",
        action="store_true",
        help="Force stamping even if the page-number box contains ink (bypass guardrail). Use with caution.",
    )
    parser.add_argument(
        "--pagenum-box",
        type=_parse_pagenum_box,
        default=None,
        help='Page number box in inches from bottom-left: "x,y,w,h"',
    )
    parser.add_argument(
        "--pagenum-size",
        type=float,
        default=10.0,
        help="Stamped page number font size in points. Default: 10.",
    )
    parser.add_argument(
        "--pagenum-font",
        choices=("Helvetica", "Times-Roman", "Courier"),
        default="Helvetica",
        help="Stamped page number font. Default: Helvetica.",
    )
    parser.add_argument(
        "--pagenum-format",
        default="{page}",
        help="Stamped page number text. Supports {page}, {roman}, and {ROMAN}.",
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
        "--debug-pypdf-xref",
        action="store_true",
        help="Capture pypdf warning events to a per-file JSON debug artifact.",
    )
    parser.add_argument(
        "--strict-xref",
        action="store_true",
        help="Fail a file when any pypdf warning is captured during processing.",
    )
    parser.add_argument(
        "--debug-render",
        action="store_true",
        help="Write per-page render diagnostics JSON files to --report-dir.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-file processing details.",
    )
    return parser


def run_cli(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    debug_pypdf_xref = bool(args.debug_pypdf_xref or args.strict_xref)
    _configure_pypdf_logging(capture_warnings=debug_pypdf_xref)
    _validate_cli_args(parser=parser, args=args)

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
        render_sample_margin=tuple(float(value) for value in args.render_sample_margin),
        white_threshold=int(args.white_threshold),
        stamp_page_numbers=bool(args.stamp_page_numbers),
        stamp_page_numbers_force=bool(args.stamp_page_numbers_force),
        pagenum_box=(
            tuple(float(value) for value in args.pagenum_box)
            if args.pagenum_box is not None
            else None
        ),
        pagenum_size=float(args.pagenum_size),
        pagenum_font=str(args.pagenum_font),
        pagenum_format=str(args.pagenum_format),
        recursive=bool(args.recursive),
        write_when_unchanged=bool(args.write_when_unchanged),
        treat_annotations_as_empty=bool(args.treat_annotations_as_empty),
        dry_run=bool(args.dry_run),
        debug_structural=bool(args.debug_structural),
        debug_pypdf_xref=debug_pypdf_xref,
        strict_xref=bool(args.strict_xref),
        debug_render=bool(args.debug_render),
        verbose=bool(args.verbose),
    )

    files = []

    report_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not run_errors and (not scan_path.exists() or not scan_path.is_dir()):
        run_errors.append(f"Scan path is not a directory: {scan_path}")
    elif not run_errors:
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
                if file_result.pypdf_warnings_path is not None:
                    print(f"wrote pypdf warnings debug to {file_result.pypdf_warnings_path}")
                if file_result.render_debug_path is not None:
                    print(f"wrote render debug to {file_result.render_debug_path}")
                if file_result.stamping_debug_path is not None:
                    print(f"wrote stamp debug to {file_result.stamping_debug_path}")

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


def _configure_pypdf_logging(capture_warnings: bool) -> None:
    """Suppress pypdf warning spam unless explicit capture is enabled."""
    logger = logging.getLogger("pypdf")
    logger.setLevel(logging.WARNING if capture_warnings else logging.ERROR)
    logger.propagate = False
    if not any(isinstance(handler, logging.NullHandler) for handler in logger.handlers):
        logger.addHandler(logging.NullHandler())


def _parse_render_sample_margin(value: str) -> RenderSampleMargin:
    """Parse TOP,LEFT,RIGHT,BOTTOM sampling margins in inches."""
    top, left, right, bottom = _parse_box_floats(
        value=value,
        label="render sample margin",
        names="TOP,LEFT,RIGHT,BOTTOM",
    )
    return (top, left, right, bottom)


def _parse_pagenum_box(value: str) -> PageNumberBox:
    """Parse x,y,w,h page-number box inches from the bottom-left origin."""
    x, y, width, height = _parse_box_floats(
        value=value,
        label="page number box",
        names="x,y,w,h",
    )
    return (x, y, width, height)


def _parse_box_floats(
    value: str,
    label: str,
    names: str,
) -> tuple[float, float, float, float]:
    """Parse four non-negative floats from a comma-separated CLI value."""
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            f"{label} must contain exactly 4 comma-separated values: {names}"
        )

    values: list[float] = []
    for part in parts:
        try:
            number = float(part)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"{label} values must be numbers in inches"
            ) from exc
        if number < 0:
            raise argparse.ArgumentTypeError(
                f"{label} values must be >= 0 inches"
            )
        values.append(number)
    first, second, third, fourth = values
    return (first, second, third, fourth)


def _validate_cli_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Validate CLI argument combinations after parsing."""
    if args.stamp_page_numbers and args.pagenum_box is None:
        parser.error("--pagenum-box is required when --stamp-page-numbers is enabled.")
    if args.stamp_page_numbers_force and not args.stamp_page_numbers:
        parser.error("--stamp-page-numbers-force requires --stamp-page-numbers.")
