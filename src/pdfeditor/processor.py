"""Single-file processing orchestration for PDFEditor."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from pypdf import PdfReader

from pdfeditor.detect_empty import detect_page_decisions
from pdfeditor.models import FileResult, PageDecision, RunConfig
from pdfeditor.rewrite import rewrite_pdf


def process_pdf(input_path: Path, out_dir: Path, config: RunConfig) -> FileResult:
    """Process one PDF and return a structured file result."""
    warnings: list[str] = []
    errors: list[str] = []
    timings: dict[str, float] = {}
    run_start = perf_counter()

    try:
        reader = PdfReader(str(input_path))
        if reader.is_encrypted:
            raise ValueError("encrypted")
    except Exception as exc:
        status_error = str(exc)
        if status_error == "encrypted":
            errors.append("encrypted")
        else:
            errors.append(f"read_error: {exc}")
        timings["total_seconds"] = round(perf_counter() - run_start, 6)
        return FileResult(
            input_path=str(input_path),
            output_path=None,
            status="failed",
            pages_original=0,
            pages_removed=0,
            pages_output=0,
            decisions_summary={"empty_pages": 0, "non_empty_pages": 0},
            page_decisions=[],
            warnings=warnings,
            errors=errors,
            timings=timings,
        )

    pages_original = len(reader.pages)

    detect_start = perf_counter()
    decisions = detect_page_decisions(
        reader=reader,
        treat_annotations_as_empty=config.treat_annotations_as_empty,
    )
    timings["detection_seconds"] = round(perf_counter() - detect_start, 6)

    pages_to_keep = [
        decision.page_index
        for decision in decisions
        if not decision.is_empty
    ]
    pages_removed = pages_original - len(pages_to_keep)
    pages_output = len(pages_to_keep) if pages_removed else pages_original

    output_path: Path | None = None
    if pages_removed > 0 or config.write_when_unchanged:
        output_path, path_warnings = build_output_path(input_path=input_path, out_dir=out_dir)
        warnings.extend(path_warnings)

    try:
        if config.dry_run:
            status = "dry_run" if pages_removed > 0 else "unchanged"
        elif pages_removed == 0 and not config.write_when_unchanged:
            status = "unchanged"
        elif output_path is None:
            status = "unchanged"
        else:
            write_start = perf_counter()
            rewrite_result = rewrite_pdf(
                input_path=input_path,
                output_path=output_path,
                pages_to_keep=pages_to_keep if pages_removed else list(range(pages_original)),
                bookmark_policy="drop",
            )
            timings["write_seconds"] = round(perf_counter() - write_start, 6)
            warnings.extend(rewrite_result.warnings)
            pages_output = rewrite_result.pages_output
            status = "edited" if pages_removed > 0 else "copied"
    except Exception as exc:
        errors.append(f"rewrite_error: {exc}")
        status = "failed"
        output_path = None
        pages_output = 0

    timings["total_seconds"] = round(perf_counter() - run_start, 6)
    return FileResult(
        input_path=str(input_path),
        output_path=str(output_path) if output_path is not None else None,
        status=status,
        pages_original=pages_original,
        pages_removed=pages_removed,
        pages_output=pages_output,
        decisions_summary=_summarize_decisions(decisions),
        page_decisions=decisions,
        warnings=warnings,
        errors=errors,
        timings=timings,
    )


def build_output_path(input_path: Path, out_dir: Path) -> tuple[Path, list[str]]:
    """Return a collision-safe edited output path for an input PDF."""
    warnings: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate = out_dir / f"{input_path.stem}.edited.pdf"
    if not candidate.exists():
        return candidate, warnings

    suffix = 1
    while True:
        candidate = out_dir / f"{input_path.stem}.edited.{suffix}.pdf"
        if not candidate.exists():
            warnings.append(
                f"Output path already existed; wrote to '{candidate.name}' instead."
            )
            return candidate, warnings
        suffix += 1


def _summarize_decisions(decisions: list[PageDecision]) -> dict[str, int]:
    summary: dict[str, int] = {
        "empty_pages": 0,
        "non_empty_pages": 0,
        "no_paint_ops_pages": 0,
        "only_invisible_paint_pages": 0,
        "visible_pages": 0,
    }
    for decision in decisions:
        summary["empty_pages" if decision.is_empty else "non_empty_pages"] += 1
        summary[decision.reason] = summary.get(decision.reason, 0) + 1
        if decision.reason == "only_invisible_paint":
            summary["only_invisible_paint_pages"] += 1
        elif decision.reason in {"no_paint_ops", "no_contents", "contents_whitespace_only"}:
            summary["no_paint_ops_pages"] += 1
        elif not decision.is_empty:
            summary["visible_pages"] += 1
    return summary
